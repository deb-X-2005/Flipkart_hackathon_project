"""Reddit RSS feeds + client-side keyword filter.
Reddit's JSON search now 403s without OAuth; their RSS feeds remain public.
"""
import re
import time
from email.utils import parsedate_to_datetime

import feedparser

from src.data.cache import get, put

DEFAULT_SUBS = ["bangalore", "karnataka", "india", "IndiaSpeaks"]


def _parse_when(s: str) -> float | None:
    try:
        return parsedate_to_datetime(s).timestamp()
    except (TypeError, ValueError):
        return None


def search(query: str, subreddits: list[str] | None = None, limit_each: int = 25, timespan_days: int = 7) -> list[dict]:
    subs = subreddits or DEFAULT_SUBS
    cache_key = f"reddit-rss:{query}:{','.join(subs)}:{limit_each}:{timespan_days}"
    cached = get(cache_key)
    if cached:
        return cached

    terms = [t.strip() for t in re.split(r"\s+|\bOR\b|,", query) if len(t.strip()) > 2]
    pattern = re.compile(r"\b(" + "|".join(re.escape(t) for t in terms) + r")\b", re.IGNORECASE) if terms else None
    cutoff = time.time() - timespan_days * 86400

    out = []
    for sub in subs:
        url = f"https://www.reddit.com/r/{sub}/new/.rss"
        try:
            feed = feedparser.parse(url)
        except Exception:
            continue
        for e in feed.entries[:limit_each]:
            title = getattr(e, "title", "") or ""
            summary = getattr(e, "summary", "") or ""
            when = _parse_when(getattr(e, "published", ""))
            if when and when < cutoff:
                continue
            if pattern and not (pattern.search(title) or pattern.search(summary)):
                continue
            out.append({
                "subreddit": sub,
                "title": title[:300],
                "link": getattr(e, "link", ""),
                "published": getattr(e, "published", ""),
                "summary": re.sub(r"<[^>]+>", " ", summary)[:600].strip(),
            })

    put(cache_key, out, ttl_seconds=1800)
    return out
