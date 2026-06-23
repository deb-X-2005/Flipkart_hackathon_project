"""OSRM routing client (public demo by default).
Falls back to a straight-line if the API is unreachable.

Self-host docs:
  https://github.com/Project-OSRM/osrm-backend
  Run a local mirror with: docker run -p 5000:5000 osrm/osrm-backend
  Then set OSRM_HOST=http://localhost:5000 in .env
"""
import os
import requests

from src.data.cache import get as cache_get, put as cache_put

HOST = os.getenv("OSRM_HOST", "https://router.project-osrm.org")


def route(from_lat: float, from_lon: float, to_lat: float, to_lon: float) -> dict:
    """Return {coords: [[lat,lon],...], distance_m: float, duration_s: float} or None on failure.
    Cached for 24 h since corridor centroids rarely change."""
    key = f"osrm:{from_lat:.4f}:{from_lon:.4f}:{to_lat:.4f}:{to_lon:.4f}"
    cached = cache_get(key)
    if cached:
        return cached
    url = (f"{HOST}/route/v1/driving/"
           f"{from_lon},{from_lat};{to_lon},{to_lat}"
           f"?overview=full&geometries=geojson&alternatives=false&steps=false")
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError):
        return _straight_line(from_lat, from_lon, to_lat, to_lon)
    if data.get("code") != "Ok" or not data.get("routes"):
        return _straight_line(from_lat, from_lon, to_lat, to_lon)
    route = data["routes"][0]
    # OSRM gives [lon, lat]; flip to [lat, lon] for Leaflet
    coords = [[lat, lon] for lon, lat in route["geometry"]["coordinates"]]
    out = {
        "coords": coords,
        "distance_m": float(route.get("distance", 0)),
        "duration_s": float(route.get("duration", 0)),
        "source": "osrm",
    }
    cache_put(key, out, ttl_seconds=86400)
    return out


def _straight_line(a_lat, a_lon, b_lat, b_lon) -> dict:
    return {
        "coords": [[a_lat, a_lon], [b_lat, b_lon]],
        "distance_m": None,
        "duration_s": None,
        "source": "fallback_straight_line",
    }
