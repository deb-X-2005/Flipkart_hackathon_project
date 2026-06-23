from src.agents.planner_agent import plan, hour_factor, nearest_diversion, corridor_centroids
import pandas as pd


def test_severity_monotonic_in_prob():
    ev = {"event_cause": "construction", "hour": 12, "is_weekend": False}
    assert plan(ev, 0.9)["severity_score"] > plan(ev, 0.1)["severity_score"]


def test_barricades_monotonic_in_prob():
    ev = {"event_cause": "construction", "hour": 12, "is_weekend": False}
    assert plan(ev, 0.9)["barricades_needed"] > plan(ev, 0.1)["barricades_needed"]


def test_crowd_by_cause_ordering():
    h = 18
    e_event = plan({"event_cause": "public_event", "hour": h}, 0.5)
    e_break = plan({"event_cause": "vehicle_breakdown", "hour": h}, 0.5)
    assert e_event["expected_crowd"] > e_break["expected_crowd"]


def test_hour_factor_rush_vs_midday_vs_late():
    assert hour_factor(9) > hour_factor(14) > hour_factor(2)
    assert hour_factor(20) > hour_factor(14)


def test_weekend_reduces_crowd():
    wd = plan({"event_cause": "construction", "hour": 9, "is_weekend": False}, 0.5)
    we = plan({"event_cause": "construction", "hour": 9, "is_weekend": True}, 0.5)
    assert we["expected_crowd"] < wd["expected_crowd"]


def test_unknown_cause_defaults():
    p = plan({"event_cause": "asteroid_strike", "hour": 12, "is_weekend": False}, 0.5)
    assert p["expected_crowd"] > 0 and p["officers_needed"] >= 1


def test_nearest_diversion_picks_different_corridor():
    df = pd.DataFrame({
        "corridor": ["A", "A", "B", "C"],
        "latitude": [12.97, 12.98, 13.0, 13.1],
        "longitude": [77.59, 77.60, 77.61, 77.7],
    })
    cents = corridor_centroids(df)
    ev = {"corridor": "A", "latitude": 12.97, "longitude": 77.59}
    d = nearest_diversion(ev, cents)
    assert d["diversion_corridor"] != "A"
    assert d["diversion_corridor"] in {"B", "C"}
