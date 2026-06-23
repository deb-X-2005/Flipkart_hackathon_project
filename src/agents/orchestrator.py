"""Master coordinator: natural-language query -> extract attrs -> forecast -> plan -> briefing."""
import json
import re
from datetime import datetime

import pandas as pd

from src.config import DATA_PROCESSED, ROOT
from src.models.forecast import load as load_model, prepare
from src.agents.planner_agent import plan as run_planner, corridor_centroids, nearest_diversion
from src.rag.retriever import retrieve as rag_retrieve
from src.llm.client import run_llm
from src.security.pii import strip as pii_strip
from src.security.audit import log as audit_log
from src.data.sources.weather import get_weather as om_weather
from src.data.sources.news import search as news_search

_state: dict = {}

VALID_CAUSES = [
    "vip_movement", "public_event", "protest", "procession", "construction",
    "accident", "tree_fall", "water_logging", "vehicle_breakdown",
    "pot_holes", "road_conditions", "congestion", "debris", "others",
]

EXTRACT_SYS = (
    "You extract structured fields from a traffic-event description for Bengaluru, India. "
    "Output STRICT JSON only — no prose, no code fences. Schema:\n"
    "{\n"
    '  "event_cause": one of ' + str(VALID_CAUSES) + ",\n"
    '  "event_type":  "planned" | "unplanned",\n'
    '  "corridor":    string (e.g. "Mysore Road", "Bellary Road 1", "Non-corridor"),\n'
    '  "hour":        integer 0-23,\n'
    '  "is_weekend":  0 or 1,\n'
    '  "latitude":    float (default 12.97),\n'
    '  "longitude":   float (default 77.59)\n'
    "}\n"
    "Infer from context. If unsure, pick the most likely value."
)


def _model():
    if "model" not in _state:
        _state["model"] = load_model(ROOT / "models" / "closure_clf.cbm")
    return _state["model"]


def _centroids():
    if "centroids" not in _state:
        df = pd.read_csv(DATA_PROCESSED / "events_with_plan.csv")
        _state["centroids"] = corridor_centroids(df)
    return _state["centroids"]


def _extract_json(text: str) -> dict:
    """LLMs sometimes wrap JSON in fences or add prose. Pull the first {...}."""
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError(f"no JSON found in LLM output: {text[:200]}")
    return json.loads(m.group(0))


def extract_event(query: str) -> dict:
    raw = run_llm(query, system=EXTRACT_SYS, temperature=0.0)
    data = _extract_json(raw)
    if data.get("event_cause") not in VALID_CAUSES:
        data["event_cause"] = "others"
    return data


def handle(query: str) -> dict:
    query = pii_strip(query)
    audit_log("orchestrator.handle", actor="user", resource=query[:100])

    attrs = extract_event(query)
    event_for_predict = {
        "event_cause": attrs["event_cause"],
        "event_type": attrs.get("event_type", "unplanned"),
        "corridor": attrs.get("corridor", "Non-corridor"),
        "priority": "High",
        "latitude": attrs.get("latitude", 12.97),
        "longitude": attrs.get("longitude", 77.59),
        "hour": attrs.get("hour", 12),
        "dow": datetime.utcnow().weekday(),
        "month": datetime.utcnow().month,
        "is_weekend": attrs.get("is_weekend", 0),
        "zone": "__missing__", "junction": "__missing__", "police_station": "__missing__",
        "requires_road_closure": False,
    }
    X, _ = prepare(pd.DataFrame([event_for_predict]))
    closure_prob = float(_model().predict_proba(X)[0, 1])

    plan = run_planner(event_for_predict, closure_prob)
    diversion = nearest_diversion(event_for_predict, _centroids())

    similar = rag_retrieve(f"{attrs['event_cause']} {attrs.get('corridor','')}", k=3)
    similar_summary = "\n".join(
        f"- {s.get('event_cause','?')} @ {s.get('corridor') or s.get('address') or '?'} (score {s['score']:.2f})"
        for s in similar if s.get("kind") == "event"
    ) or "(no prior similar events)"

    # Fetch live signals related to this event (best-effort, cached, never blocks)
    weather_summary, news_summary = "(weather unavailable)", "(no current news)"
    try:
        w = om_weather(attrs.get("latitude", 12.97), attrs.get("longitude", 77.59), hours=6)
        h = w.get("hourly", {})
        temps = h.get("temperature_2m", [])
        rains = h.get("precipitation", [])
        if temps:
            weather_summary = (
                f"next 6h: {min(temps):.0f}-{max(temps):.0f}°C, "
                f"{sum(rains):.1f} mm rain"
            )
    except Exception:
        pass
    try:
        q_news = f"{attrs.get('corridor','Bengaluru')} {attrs['event_cause'].replace('_',' ')}"
        items = news_search(pii_strip(q_news), limit=4)
        if items:
            news_summary = "\n".join(f"- {i.get('source','?')}: {i.get('title','')[:120]}" for i in items[:4])
    except Exception:
        pass

    briefing_prompt = f"""You are briefing a Bengaluru traffic officer. Write a 4-6 sentence briefing.
Ground every claim in the data below. If weather or current news change the picture, mention it.

Event: {query}
Extracted attributes: {attrs}
Forecast: closure probability {closure_prob:.0%}, severity score {plan['severity_score']:.2f}
Plan: {plan['expected_crowd']:,} expected attendees, deploy {plan['officers_needed']} officers and {plan['barricades_needed']} barricades.
Diversion target: {diversion['diversion_corridor']}.

Similar past events:
{similar_summary}

Current weather at the event location:
{weather_summary}

Recent news matching this event/corridor:
{news_summary}

Briefing:"""

    try:
        briefing = run_llm(briefing_prompt, temperature=0.3)
    except Exception as e:
        briefing = f"(LLM error: {e}) — plan stands as listed."

    return {
        "query": query,
        "extracted": attrs,
        "forecast": {"closure_prob": round(closure_prob, 3)},
        "plan": {**plan, **diversion},
        "similar_events": similar,
        "context": {
            "weather": weather_summary,
            "news": news_summary,
        },
        "briefing": briefing.strip(),
    }
