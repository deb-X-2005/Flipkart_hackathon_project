"""Rule-based planner: closure_prob + event attrs -> resource plan + diversion."""
import math
import pandas as pd
import numpy as np

CAUSE_CROWD = {
    "public_event": 2000, "procession": 1500, "vip_movement": 1000,
    "protest": 800, "congestion": 600, "accident": 300,
    "construction": 200, "fog / low visibility": 200, "water_logging": 150,
    "road_conditions": 100, "tree_fall": 100, "debris": 80, "pot_holes": 80,
    "vehicle_breakdown": 50, "others": 100,
}

CAUSE_SEVERITY = {
    "vip_movement": 3.0, "public_event": 2.5, "protest": 2.5, "procession": 2.2,
    "construction": 2.0, "tree_fall": 1.8, "accident": 1.8, "water_logging": 1.5,
    "fog / low visibility": 1.5, "congestion": 1.3, "road_conditions": 1.0,
    "debris": 1.0, "pot_holes": 0.7, "vehicle_breakdown": 0.5, "others": 0.7,
}


def hour_factor(hour) -> float:
    if hour is None or pd.isna(hour):
        return 1.0
    h = int(hour)
    if 8 <= h <= 10 or 18 <= h <= 21:
        return 1.5
    if 11 <= h <= 16:
        return 1.0
    if h >= 22 or h <= 4:
        return 0.4
    return 0.8


def plan(event: dict, closure_prob: float) -> dict:
    cause = (event.get("event_cause") or "others")
    base = CAUSE_CROWD.get(cause, 200)
    sev = CAUSE_SEVERITY.get(cause, 1.0)
    hf = hour_factor(event.get("hour"))
    if event.get("is_weekend"):
        hf *= 0.85
    crowd = int(base * hf)
    barricades = max(1, math.ceil(closure_prob * sev * 5))
    officers = max(1, math.ceil(crowd / 200) + math.ceil(barricades / 3))
    score = float(np.clip(closure_prob * sev / 3.0, 0.0, 1.0))
    return {
        "closure_prob": round(float(closure_prob), 3),
        "expected_crowd": crowd,
        "barricades_needed": int(barricades),
        "officers_needed": int(officers),
        "severity_score": round(score, 3),
    }


def corridor_centroids(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.dropna(subset=["latitude", "longitude", "corridor"])
        .groupby("corridor")[["latitude", "longitude"]]
        .mean()
    )


def nearest_diversion(event: dict, centroids: pd.DataFrame) -> dict:
    own = event.get("corridor")
    pool = centroids.drop(index=own, errors="ignore") if own in centroids.index else centroids
    if pool.empty:
        return {"diversion_corridor": None, "diversion_lat": None, "diversion_lon": None}
    lat, lon = event["latitude"], event["longitude"]
    d2 = (pool["latitude"] - lat) ** 2 + (pool["longitude"] - lon) ** 2
    name = d2.idxmin()
    row = pool.loc[name]
    return {
        "diversion_corridor": str(name),
        "diversion_lat": float(row["latitude"]),
        "diversion_lon": float(row["longitude"]),
    }
