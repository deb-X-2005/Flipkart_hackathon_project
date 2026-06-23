"""data.gov.in client. API key optional; without it, returns a warning."""
import os
import requests

from src.data.cache import get, put

BASE = "https://api.data.gov.in/resource"


def _key() -> str:
    return os.getenv("DATAGOV_API_KEY", "")


def query_resource(resource_id: str, filters: dict | None = None, limit: int = 100) -> dict:
    if not _key():
        return {"records": [], "warning": "DATAGOV_API_KEY not set in .env; data.gov.in skipped"}
    cache_key = f"datagov:{resource_id}:{filters}:{limit}"
    cached = get(cache_key)
    if cached:
        return cached
    params = {"api-key": _key(), "format": "json", "limit": limit}
    if filters:
        for k, v in filters.items():
            params[f"filters[{k}]"] = v
    r = requests.get(f"{BASE}/{resource_id}", params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    put(cache_key, data, ttl_seconds=86400)
    return data
