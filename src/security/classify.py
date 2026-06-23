"""Data classification registry. ISO 27001 A.8.2.

Each event-data field is tagged:
  public    - no restriction (event_type, event_cause, corridor)
  internal  - share only with operators (priority, severity_score, plan fields)
  sensitive - PII or close to it; encrypt at rest, strip from public outputs
"""
from typing import Iterable

REGISTRY: dict[str, str] = {
    # public
    "event_type": "public", "event_cause": "public", "corridor": "public",
    "zone": "public", "junction": "public", "status": "public",
    "start_datetime": "public", "end_datetime": "public",
    "latitude": "public", "longitude": "public",
    "hour": "public", "dow": "public", "month": "public", "is_weekend": "public",
    # internal
    "priority": "internal", "requires_road_closure": "internal",
    "closure_prob": "internal", "expected_crowd": "internal",
    "barricades_needed": "internal", "officers_needed": "internal",
    "severity_score": "internal", "diversion_corridor": "internal",
    "police_station": "internal", "direction": "internal",
    # sensitive
    "address": "sensitive", "end_address": "sensitive",
    "resolved_at_address": "sensitive", "description": "sensitive",
    "veh_no": "sensitive", "cargo_material": "sensitive",
    "client_id": "sensitive", "created_by_id": "sensitive",
    "kgid": "sensitive", "citizen_accident_id": "sensitive",
    "assigned_to_police_id": "sensitive", "closed_by_id": "sensitive",
    "resolved_by_id": "sensitive",
}

CLASS_RANK = {"public": 0, "internal": 1, "sensitive": 2}


def classify(field: str) -> str:
    return REGISTRY.get(field, "internal")  # default conservatively


def fields_at_most(level: str, fields: Iterable[str]) -> list[str]:
    ceiling = CLASS_RANK[level]
    return [f for f in fields if CLASS_RANK.get(classify(f), 1) <= ceiling]


def project(row: dict, max_level: str) -> dict:
    """Drop fields above max_level from a dict (e.g. for viewer-role responses)."""
    return {k: v for k, v in row.items() if CLASS_RANK.get(classify(k), 1) <= CLASS_RANK[max_level]}
