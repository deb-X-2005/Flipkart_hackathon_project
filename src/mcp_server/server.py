"""MCP server exposing traffic-forecasting tools to any MCP-compatible AI agent.

Tools: forecast_closure, plan_resources, forecast_and_plan, retrieve_similar_events,
get_weather, get_news, get_reddit, get_gdelt, erase_event.

Run:
  python -m src.mcp_server.server          (stdio - Claude Desktop)
  MCP_TRANSPORT=http python -m src.mcp_server.server   (streamable HTTP on :8765)

Every call is PII-stripped on text inputs and audit-logged.
"""
import os
import pandas as pd
from mcp.server.fastmcp import FastMCP

from src.config import DATA_PROCESSED, ROOT
from src.models.forecast import load as load_model, prepare
from src.agents.planner_agent import plan as run_planner, corridor_centroids, nearest_diversion
from src.rag.retriever import retrieve as rag_retrieve
from src.data.sources.weather import get_weather as om_weather
from src.data.sources.news import search as news_search
from src.data.sources.reddit import search as reddit_search
from src.data.sources.gdelt import search_events as gdelt_search
from src.security.pii import strip as pii_strip
from src.security.audit import log as audit_log
from src.security.erasure import erase as gdpr_erase

mcp = FastMCP("event-traffic")

_state: dict = {}


def _model():
    if "model" not in _state:
        _state["model"] = load_model(ROOT / "models" / "closure_clf.cbm")
    return _state["model"]


def _centroids():
    if "centroids" not in _state:
        df = pd.read_csv(DATA_PROCESSED / "events_with_plan.csv")
        _state["centroids"] = corridor_centroids(df)
    return _state["centroids"]


@mcp.tool()
def forecast_closure(
    event_cause: str,
    corridor: str = "Non-corridor",
    event_type: str = "unplanned",
    priority: str = "High",
    latitude: float = 12.97,
    longitude: float = 77.59,
    hour: int = 12,
    dow: int = 1,
    month: int = 6,
    is_weekend: int = 0,
    zone: str = "__missing__",
    junction: str = "__missing__",
    police_station: str = "__missing__",
) -> dict:
    """Predict probability that a given event requires a road closure.
    Returns {"closure_prob": float in [0,1], "event_cause": str, "corridor": str}.
    """
    row = {
        "event_cause": event_cause, "event_type": event_type, "corridor": corridor,
        "priority": priority, "latitude": latitude, "longitude": longitude,
        "hour": hour, "dow": dow, "month": month, "is_weekend": is_weekend,
        "zone": zone, "junction": junction, "police_station": police_station,
        "requires_road_closure": False,
    }
    X, _ = prepare(pd.DataFrame([row]))
    prob = float(_model().predict_proba(X)[0, 1])
    audit_log("mcp.forecast_closure", actor="mcp_client",
              resource=f"event:{event_cause}", closure_prob=round(prob, 3))
    return {"closure_prob": round(prob, 3), "event_cause": event_cause, "corridor": corridor}


@mcp.tool()
def plan_resources(
    event_cause: str,
    closure_prob: float,
    hour: int = 12,
    is_weekend: int = 0,
    corridor: str = "Non-corridor",
    latitude: float = 12.97,
    longitude: float = 77.59,
) -> dict:
    """Turn a closure probability into operational outputs: barricades, officers,
    expected crowd, severity score, and a diversion target corridor.
    """
    event = {"event_cause": event_cause, "hour": hour, "is_weekend": bool(is_weekend),
             "corridor": corridor, "latitude": latitude, "longitude": longitude}
    plan = run_planner(event, closure_prob)
    div = nearest_diversion(event, _centroids())
    out = {**plan, **div}
    audit_log("mcp.plan_resources", actor="mcp_client",
              resource=f"event:{event_cause}", severity=plan["severity_score"])
    return out


@mcp.tool()
def forecast_and_plan(
    event_cause: str,
    corridor: str = "Non-corridor",
    event_type: str = "unplanned",
    hour: int = 12,
    is_weekend: int = 0,
    latitude: float = 12.97,
    longitude: float = 77.59,
) -> dict:
    """One-shot: forecast closure probability and return the full resource plan."""
    fc = forecast_closure(event_cause=event_cause, corridor=corridor, event_type=event_type,
                          hour=hour, is_weekend=is_weekend,
                          latitude=latitude, longitude=longitude)
    pl = plan_resources(event_cause=event_cause, closure_prob=fc["closure_prob"],
                        hour=hour, is_weekend=is_weekend, corridor=corridor,
                        latitude=latitude, longitude=longitude)
    return {**fc, **pl}


@mcp.tool()
def retrieve_similar_events(query: str, k: int = 5) -> list[dict]:
    """RAG: top-k semantically similar past events / news / reddit posts."""
    safe = pii_strip(query)
    audit_log("mcp.rag_retrieve", actor="mcp_client", resource=safe[:80], k=k)
    return rag_retrieve(safe, k=k)


@mcp.tool()
def get_weather(latitude: float, longitude: float, hours: int = 6) -> dict:
    """6-hour weather forecast at a coordinate (Open-Meteo, free)."""
    audit_log("mcp.weather", actor="mcp_client",
              resource=f"{latitude:.3f},{longitude:.3f}", hours=hours)
    return om_weather(latitude, longitude, hours=hours)


@mcp.tool()
def get_news(query: str, limit: int = 10) -> list[dict]:
    """Google News RSS (India locale)."""
    safe = pii_strip(query)
    audit_log("mcp.news", actor="mcp_client", resource=safe[:80], limit=limit)
    return news_search(safe, limit=limit)


@mcp.tool()
def get_reddit(query: str, limit_each: int = 10, timespan_days: int = 7) -> list[dict]:
    """Reddit RSS (r/bangalore, r/karnataka, r/india, r/IndiaSpeaks). Keyword-filtered."""
    safe = pii_strip(query)
    audit_log("mcp.reddit", actor="mcp_client", resource=safe[:80], limit=limit_each)
    return reddit_search(safe, limit_each=limit_each, timespan_days=timespan_days)


@mcp.tool()
def get_gdelt(query: str, maxrecords: int = 10, timespan: str = "1d") -> dict:
    """GDELT 2.0 article search for news-detected events."""
    safe = pii_strip(query)
    audit_log("mcp.gdelt", actor="mcp_client", resource=safe[:80])
    return gdelt_search(safe, maxrecords=maxrecords, timespan=timespan)


@mcp.tool()
def erase_event(event_id: str, actor: str = "mcp_client") -> dict:
    """GDPR Art 17 right-to-erasure. Removes an event from CSV + FAISS + cache."""
    return gdpr_erase(event_id=event_id, actor=actor)


class _AuthMiddleware:
    """ASGI middleware that requires Bearer token (JWT or MCP token) on HTTP transport."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        if scope["path"] in ("/healthz", "/"):
            return await self.app(scope, receive, send)
        from src.security import auth as sec_auth
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        bearer = headers.get("authorization", "")
        if not bearer.lower().startswith("bearer "):
            audit_log("mcp.auth.missing", actor="unknown", outcome="fail", path=scope["path"])
            return await _send_401(send, "missing bearer token")
        token = bearer.split(" ", 1)[1]
        try:
            claims = sec_auth.verify_any(token)
        except Exception as e:
            audit_log("mcp.auth.invalid", actor="unknown", outcome="fail", reason=str(e))
            return await _send_401(send, "invalid token")
        audit_log("mcp.auth.ok", actor=claims.get("sub", "?"),
                  role=claims.get("role", "?"), aud=claims.get("aud"))
        scope["state"] = {**scope.get("state", {}), "principal": claims}
        return await self.app(scope, receive, send)


async def _send_401(send, msg: str) -> None:
    import json as _json
    body = _json.dumps({"error": msg}).encode()
    await send({"type": "http.response.start", "status": 401,
                "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": body})


def http_app():
    """Return the streamable-HTTP ASGI app wrapped in the auth middleware."""
    inner = mcp.streamable_http_app()
    return _AuthMiddleware(inner)


def main() -> None:
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "http":
        import uvicorn
        host = os.getenv("MCP_HOST", "127.0.0.1")
        port = int(os.getenv("MCP_PORT", "8765"))
        uvicorn.run(http_app(), host=host, port=port, log_level="warning")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
