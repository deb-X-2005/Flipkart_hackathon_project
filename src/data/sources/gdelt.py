"""GDELT 2.0 Doc API. Free, no key. Use for news-detected events."""
import requests

from src.data.cache import get, put

URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def search_events(query: str = "Karnataka traffic", maxrecords: int = 25, timespan: str = "1d") -> dict:
    cache_key = f"gdelt:{query}:{maxrecords}:{timespan}"
    cached = get(cache_key)
    if cached:
        return cached
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "JSON",
        "maxrecords": maxrecords,
        "timespan": timespan,
    }
    try:
        r = requests.get(URL, params=params, timeout=15)
        r.raise_for_status()
    except requests.RequestException as e:
        return {"articles": [], "error": str(e)}
    try:
        data = r.json()
    except ValueError:
        return {"articles": [], "error": "non-JSON response"}
    put(cache_key, data, ttl_seconds=1800)
    return data
