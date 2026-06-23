"""Google News RSS. Free, no key. India locale by default."""
import feedparser

from src.data.cache import get, put

BASE = "https://news.google.com/rss/search"


def search(query: str, lang: str = "en-IN", country: str = "IN", limit: int = 30) -> list[dict]:
    cache_key = f"news:{query}:{lang}:{country}:{limit}"
    cached = get(cache_key)
    if cached:
        return cached
    url = f"{BASE}?q={requests_quote(query)}&hl={lang}&gl={country}&ceid={country}:{lang.split('-')[0]}"
    parsed = feedparser.parse(url)
    items = []
    for e in parsed.entries[:limit]:
        items.append({
            "title": getattr(e, "title", ""),
            "link": getattr(e, "link", ""),
            "published": getattr(e, "published", ""),
            "source": getattr(getattr(e, "source", None), "title", "") or "",
            "summary": getattr(e, "summary", "")[:600],
        })
    put(cache_key, items, ttl_seconds=1800)
    return items


def requests_quote(s: str) -> str:
    from urllib.parse import quote_plus
    return quote_plus(s)
