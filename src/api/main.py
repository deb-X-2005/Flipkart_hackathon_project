"""FastAPI backend exposing every capability: events, forecast, plan, chat, rag, realtime, erasure.

Run:
  uvicorn src.api.main:app --reload --port 8000
"""
import math
import os
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.api.schemas import (
    LoginIn, SignupIn, TokenOut, EventAttrs, ForecastOut, PlanIn, PlanOut, ChatIn, RagIn,
)
from src.config import DATA_PROCESSED, ROOT
from src.security.auth import (
    issue, current_user, require_role, DEFAULT_TTL,
)
from src.security.audit import log as audit_log
from src.security.classify import project as cls_project
from src.security.erasure import erase as gdpr_erase

# ML / RAG
from src.models.forecast import load as load_model, prepare
from src.agents.planner_agent import plan as run_planner, corridor_centroids, nearest_diversion
from src.rag.retriever import retrieve as rag_retrieve
from src.agents.orchestrator import handle as orchestrate

# Realtime sources
from src.data.sources.weather import get_weather as om_weather
from src.data.sources.news import search as news_search
from src.data.sources.reddit import search as reddit_search
from src.data.sources.gdelt import search_events as gdelt_search


os.environ.setdefault("AUTH_SECRET", "dev-only-replace-with-token_urlsafe-48")


def _rate_key(request: Request) -> str:
    """Limit by JWT subject if present, else by IP."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1]
        try:
            import jwt as _jwt
            from src.security.auth import _secret, ALG
            claims = _jwt.decode(token, _secret(), algorithms=[ALG], options={"verify_aud": False})
            return f"sub:{claims.get('sub','unknown')}"
        except Exception:
            pass
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=_rate_key, default_limits=["120/minute"])

app = FastAPI(title="Event Traffic Forecasting", version="0.1")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
_extra_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", *_extra_origins],
    allow_methods=["*"], allow_headers=["*"], allow_credentials=True,
)

# OIDC SSO (only active when OIDC_PROVIDER + OIDC_CLIENT_ID are set in env)
try:
    from src.api.oidc import router as oidc_router, install_session_middleware
    install_session_middleware(app, secret=os.getenv("AUTH_SECRET", "dev"))
    app.include_router(oidc_router)
except Exception:
    pass

# Prometheus metrics at /metrics-prom (avoid clash with our /metrics KPI endpoint)
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator(
        should_group_status_codes=False,
        excluded_handlers=["/metrics-prom"],
    ).instrument(app).expose(app, endpoint="/metrics-prom", include_in_schema=False)
except Exception:
    pass  # metrics endpoint not critical for the demo

_state: dict = {}


def _model():
    if "model" not in _state:
        _state["model"] = load_model(ROOT / "models" / "closure_clf.cbm")
    return _state["model"]


def _events_df() -> pd.DataFrame:
    if "events" not in _state:
        _state["events"] = pd.read_csv(DATA_PROCESSED / "events_with_plan.csv")
    return _state["events"]


def _centroids():
    if "centroids" not in _state:
        _state["centroids"] = corridor_centroids(_events_df())
    return _state["centroids"]


def _clean(rec: dict) -> dict:
    out = {}
    for k, v in rec.items():
        if isinstance(v, float) and not math.isfinite(v):
            out[k] = None
        else:
            out[k] = v
    return out


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/login", response_model=TokenOut)
def login(body: LoginIn):
    """Password login against the local user store. SSO/OIDC available separately."""
    from src.security.users import authenticate
    if not body.password:
        # Legacy "demo role" path — only allowed in dev (when AUTH_ALLOW_DEMO is set)
        if os.getenv("AUTH_ALLOW_DEMO") == "1" and body.role in {"viewer", "operator", "admin"}:
            return TokenOut(token=issue(body.username, body.role), expires_in=DEFAULT_TTL)
        raise HTTPException(400, "password required")
    role = authenticate(body.username, body.password)
    if not role:
        audit_log("auth.login_fail", actor=body.username, outcome="fail")
        raise HTTPException(401, "invalid credentials")
    audit_log("auth.login_ok", actor=body.username, role=role)
    return TokenOut(token=issue(body.username, role), expires_in=DEFAULT_TTL)


@app.get("/auth/demo-users")
def demo_users():
    """Public list of seed accounts so users can sign in without setup."""
    from src.security.users import list_demo_users
    return {"users": list_demo_users()}


@app.post("/auth/signup", response_model=TokenOut)
def signup(body: SignupIn):
    """Create a new account and return a JWT.
    Demo-grade: caller picks the role. Production: defaults to viewer + admin promotes via separate flow."""
    from src.security.users import create
    role = body.role if body.role in {"viewer", "operator", "admin"} else "operator"
    if not create(body.username, body.password, role=role):
        audit_log("auth.signup_fail", actor=body.username, outcome="fail")
        raise HTTPException(409, "username taken or invalid")
    audit_log("auth.signup_ok", actor=body.username, role=role)
    return TokenOut(token=issue(body.username, role), expires_in=DEFAULT_TTL)


@app.get("/events")
def list_events(
    limit: int = Query(200, ge=1, le=2000),
    offset: int = 0,
    cause: str | None = None,
    corridor: str | None = None,
    min_severity: float = 0.0,
    from_date: str | None = Query(None, description="YYYY-MM-DD inclusive"),
    to_date: str | None = Query(None, description="YYYY-MM-DD inclusive"),
    user: dict = Depends(current_user),
):
    df = _events_df()
    if cause:
        df = df[df["event_cause"] == cause]
    if corridor:
        df = df[df["corridor"] == corridor]
    if min_severity:
        df = df[df["severity_score"].fillna(0) >= min_severity]
    if from_date or to_date:
        s = pd.to_datetime(df["start_datetime"], errors="coerce")
        if from_date:
            df = df[s >= from_date]
        if to_date:
            df = df[s <= to_date + " 23:59:59"]
    rows = df.iloc[offset: offset + limit].to_dict(orient="records")
    level = {"viewer": "public", "operator": "internal", "admin": "sensitive"}[user["role"]]
    rows = [_clean(cls_project(r, level)) for r in rows]
    audit_log("api.events.list", actor=user["sub"], outcome="ok", count=len(rows), filters={"cause": cause, "corridor": corridor})
    return {"count": len(rows), "total": int(len(df)), "items": rows}


@app.get("/events/facets")
def events_facets(user: dict = Depends(current_user)):
    df = _events_df()
    return {
        "causes": sorted(df["event_cause"].dropna().unique().tolist()),
        "corridors": df["corridor"].fillna("Non-corridor").value_counts().head(30).index.tolist(),
        "date_range": [str(df["start_datetime"].min())[:10], str(df["start_datetime"].max())[:10]],
    }


@app.get("/metrics")
def metrics(user: dict = Depends(current_user)):
    df = _events_df()
    severe = df[df["severity_score"].fillna(0) >= 0.3]
    return {
        "total_events": int(len(df)),
        "severe_events": int(len(severe)),
        "severe_pct": round(len(severe) / max(len(df), 1) * 100, 1),
        "expected_crowd_sum": int(severe["expected_crowd"].sum()),
        "barricades_needed_sum": int(severe["barricades_needed"].sum()),
        "officers_needed_sum": int(severe["officers_needed"].sum()),
        "top_cause": severe["event_cause"].mode().iloc[0] if len(severe) else None,
        "top_corridor": severe["corridor"].mode().iloc[0] if len(severe) else None,
        "time_range": [str(df["start_datetime"].min())[:10], str(df["start_datetime"].max())[:10]],
    }


@app.post("/forecast", response_model=ForecastOut)
@limiter.limit("60/minute")
def forecast(request: Request, attrs: EventAttrs, user: dict = Depends(require_role("operator"))):
    row = attrs.model_dump()
    row["requires_road_closure"] = False
    X, _ = prepare(pd.DataFrame([row]))
    prob = float(_model().predict_proba(X)[0, 1])
    audit_log("api.forecast", actor=user["sub"], resource=f"event:{attrs.event_cause}", closure_prob=round(prob, 3))
    return ForecastOut(closure_prob=round(prob, 3))


@app.post("/plan", response_model=PlanOut)
def plan_endpoint(body: PlanIn, user: dict = Depends(require_role("operator"))):
    event = body.model_dump()
    closure_prob = event.pop("closure_prob")
    p = run_planner(event, closure_prob)
    d = nearest_diversion(event, _centroids())
    audit_log("api.plan", actor=user["sub"], resource=f"event:{body.event_cause}", severity=p["severity_score"])
    return PlanOut(**p, **d)


@app.post("/forecast-and-plan", response_model=PlanOut)
@limiter.limit("60/minute")
def forecast_and_plan(request: Request, attrs: EventAttrs, user: dict = Depends(require_role("operator"))):
    row = attrs.model_dump()
    row["requires_road_closure"] = False
    X, _ = prepare(pd.DataFrame([row]))
    prob = float(_model().predict_proba(X)[0, 1])
    event = attrs.model_dump()
    p = run_planner(event, prob)
    d = nearest_diversion(event, _centroids())
    audit_log("api.forecast_and_plan", actor=user["sub"], resource=f"event:{attrs.event_cause}", closure_prob=round(prob, 3))
    return PlanOut(**p, **d)


@app.post("/chat")
@limiter.limit("10/minute")
def chat(request: Request, body: ChatIn, user: dict = Depends(require_role("operator"))):
    audit_log("api.chat", actor=user["sub"], resource=body.query[:100])
    try:
        return orchestrate(body.query)
    except Exception as e:
        audit_log("api.chat.fail", actor=user["sub"], outcome="fail", error=type(e).__name__, msg=str(e)[:200])
        raise HTTPException(502, f"LLM/RAG pipeline failed: {type(e).__name__}: {str(e)[:200]}")


@app.post("/rag/retrieve")
@limiter.limit("30/minute")
def rag(request: Request, body: RagIn, user: dict = Depends(current_user)):
    audit_log("api.rag", actor=user["sub"], resource=body.query[:100], k=body.k)
    return {"results": rag_retrieve(body.query, k=body.k)}


@app.get("/realtime/weather")
def realtime_weather(lat: float = 12.97, lon: float = 77.59, hours: int = 6,
                     user: dict = Depends(current_user)):
    return om_weather(lat, lon, hours=hours)


def _ground_query(q: str) -> str:
    """If query has no Bengaluru/Karnataka anchor, append one so results stay local."""
    lower = q.lower()
    if any(t in lower for t in ("bengaluru", "bangalore", "karnataka")):
        return q
    return f"{q} Bengaluru"


@app.get("/realtime/news")
def realtime_news(q: str = "Bangalore traffic", limit: int = 10,
                  user: dict = Depends(current_user)):
    return {"items": news_search(_ground_query(q), limit=limit)}


@app.get("/realtime/reddit")
def realtime_reddit(q: str = "Bangalore traffic", limit_each: int = 10, days: int = 7,
                    user: dict = Depends(current_user)):
    return {"items": reddit_search(_ground_query(q), limit_each=limit_each, timespan_days=days)}


@app.get("/realtime/gdelt")
def realtime_gdelt(q: str = "Karnataka traffic", limit: int = 10, timespan: str = "1d",
                   user: dict = Depends(current_user)):
    return gdelt_search(q, maxrecords=limit, timespan=timespan)


@app.delete("/events/{event_id}")
def erase(event_id: str, user: dict = Depends(require_role("admin"))):
    return gdpr_erase(event_id=event_id, actor=user["sub"])


@app.post("/llm/settings")
def llm_settings(body: dict, user: dict = Depends(require_role("admin"))):
    """Update LLM_MODE / model / API key at runtime. Admin only.
    Verifies the new config with a 1-token probe before committing.
    """
    mode = (body.get("mode") or "").strip().lower()
    model = body.get("model") or None
    key = body.get("api_key") or None
    if mode and mode not in {"ollama", "openai", "anthropic", "openrouter"}:
        raise HTTPException(400, f"unknown mode '{mode}'")

    # Snapshot current env so we can roll back on failure
    snapshot = {k: os.environ.get(k) for k in (
        "LLM_MODE", "OLLAMA_MODEL", "OPENAI_MODEL", "ANTHROPIC_MODEL",
        "OPENROUTER_MODEL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY",
    )}

    if mode: os.environ["LLM_MODE"] = mode
    if model:
        os.environ[{"openai": "OPENAI_MODEL", "anthropic": "ANTHROPIC_MODEL",
                    "openrouter": "OPENROUTER_MODEL", "ollama": "OLLAMA_MODEL"}[mode]] = model
    if key:
        os.environ[{"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
                    "openrouter": "OPENROUTER_API_KEY"}.get(mode, "_unused")] = key

    # Probe: try a minimal call. Cheap for cloud (1 token), instant for Ollama.
    try:
        from src.llm.client import run_llm
        run_llm("ok", temperature=0.0)
    except Exception as e:
        # Roll back
        for k, v in snapshot.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v
        audit_log("llm.settings_rejected", actor=user["sub"], mode=mode, reason=str(e)[:200])
        raise HTTPException(400, f"new LLM config failed probe: {type(e).__name__}: {str(e)[:200]}")

    audit_log("llm.settings_changed", actor=user["sub"], mode=mode, model_set=bool(model), key_set=bool(key))
    return {"ok": True, "active_mode": os.environ.get("LLM_MODE")}


@app.post("/llm/probe")
def llm_probe(body: dict, user: dict = Depends(require_role("admin"))):
    """Test a candidate LLM config without committing it. Body: {mode, model?, api_key?}.
    Sets env vars in a snapshot/restore wrapper, runs a 1-token call, returns the verdict.
    """
    mode = (body.get("mode") or "").strip().lower()
    if mode not in {"ollama", "openai", "anthropic", "openrouter"}:
        raise HTTPException(400, f"unknown mode '{mode}'")
    model = body.get("model") or None
    key = body.get("api_key") or None

    snapshot = {k: os.environ.get(k) for k in (
        "LLM_MODE", "OLLAMA_MODEL", "OPENAI_MODEL", "ANTHROPIC_MODEL",
        "OPENROUTER_MODEL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY",
    )}
    try:
        os.environ["LLM_MODE"] = mode
        if model:
            os.environ[{"openai": "OPENAI_MODEL", "anthropic": "ANTHROPIC_MODEL",
                        "openrouter": "OPENROUTER_MODEL", "ollama": "OLLAMA_MODEL"}[mode]] = model
        if key:
            env_key = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
                       "openrouter": "OPENROUTER_API_KEY"}.get(mode)
            if env_key: os.environ[env_key] = key
        from src.llm.client import run_llm
        out = run_llm("ok", temperature=0.0)
        result = {"ok": True, "sample_response": (out or "")[:120]}
    except Exception as e:
        result = {"ok": False, "error_type": type(e).__name__, "error": str(e)[:400]}
    finally:
        for k, v in snapshot.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v
    audit_log("llm.probe", actor=user["sub"], mode=mode, outcome="ok" if result["ok"] else "fail")
    return result


@app.get("/llm/search")
def llm_search(q: str = "", user: dict = Depends(current_user)):
    """Search Ollama library for pullable models."""
    from src.llm import ollama as _oll
    return {"items": _oll.search_library(q, limit=15)}


@app.post("/llm/pull")
def llm_pull(body: dict, user: dict = Depends(require_role("admin"))):
    """Pull an Ollama model. Streams events into the audit log.
    Body: {model: "llama3.2:3b"}"""
    from src.llm import ollama as _oll
    name = body.get("model", "").strip()
    if not name:
        raise HTTPException(400, "model required")
    last = None
    total = 0
    for evt in _oll.pull(name):
        s = evt.get("status")
        if s != last:
            audit_log("llm.pull.progress", actor=user["sub"], model=name, status=s)
            last = s
        if evt.get("completed"):
            total = evt["completed"]
    return {"ok": True, "model": name, "bytes": total}


@app.get("/llm/info")
def llm_info(user: dict = Depends(current_user)):
    from src.llm.client import resolved_mode
    from src.llm import ollama as _oll
    try:
        mode = resolved_mode()
    except Exception as e:
        return {"mode": None, "error": str(e), "ollama_running": _oll.health()}
    info = {"mode": mode, "ollama_running": _oll.health()}
    if mode == "ollama" and info["ollama_running"]:
        info["default_model"] = _oll.DEFAULT_MODEL
        try:
            info["installed_models"] = [m.get("name") for m in _oll.list_local()]
        except Exception:
            info["installed_models"] = []
    elif mode == "openai":
        info["default_model"] = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    elif mode == "anthropic":
        info["default_model"] = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    elif mode == "openrouter":
        info["default_model"] = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.5")
    return info


@app.get("/routing/diversion")
def routing_diversion(from_lat: float, from_lon: float, to_lat: float, to_lon: float,
                       user: dict = Depends(current_user)):
    from src.data.sources.osrm import route
    return route(from_lat, from_lon, to_lat, to_lon)


@app.get("/heatmap.html", response_class=HTMLResponse)
def heatmap():
    path = ROOT / "reports" / "heatmap_karnataka.html"
    if not path.exists():
        raise HTTPException(404, "run scripts/stage6_karnataka_map.py first")
    return HTMLResponse(path.read_text(encoding="utf-8"))


# Serve the built React frontend from /app/static when present (production single-container deploy).
# This must be mounted LAST so all API routes above win route matching.
_STATIC_DIR = ROOT / "static"
if _STATIC_DIR.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
