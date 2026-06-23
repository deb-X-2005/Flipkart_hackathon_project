"""Bengaluru Traffic Police advisories. HTML scrape; selectors may shift."""
import requests
from bs4 import BeautifulSoup

from src.data.cache import get, put

URL = "https://btp.karnataka.gov.in/page/Traffic+Advisories/en"
HEADERS = {"User-Agent": "Mozilla/5.0 (research; contact: admin@example.com)"}


def fetch_advisories(limit: int = 20) -> list[dict]:
    cache_key = f"btp:advisories:{limit}"
    cached = get(cache_key)
    if cached:
        return cached
    try:
        r = requests.get(URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except requests.RequestException as e:
        return [{"error": str(e), "source": "BTP"}]
    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    for el in soup.select("table tr"):
        cells = [c.get_text(" ", strip=True) for c in el.find_all("td")]
        if cells and any(cells):
            items.append({"row": cells})
        if len(items) >= limit:
            break
    put(cache_key, items, ttl_seconds=1800)
    return items
