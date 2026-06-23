"""Open-Meteo weather client. Free, no key required."""
import requests

from src.data.cache import get, put

BASE = "https://api.open-meteo.com/v1/forecast"


def get_weather(lat: float, lon: float, hours: int = 6) -> dict:
    key = f"weather:{lat:.3f}:{lon:.3f}:{hours}"
    cached = get(key)
    if cached:
        return cached
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation,wind_speed_10m,visibility,weathercode",
        "forecast_hours": hours,
        "timezone": "Asia/Kolkata",
    }
    r = requests.get(BASE, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    put(key, data, ttl_seconds=3600)
    return data
