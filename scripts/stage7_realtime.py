"""Stage 7: smoke-test all real-time govt/news sources.
Hits each, reports counts, caches to data/cache.sqlite.
"""
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.sources.weather import get_weather
from src.data.sources.datagov import query_resource
from src.data.sources.btp import fetch_advisories
from src.data.sources.gdelt import search_events


def main() -> None:
    print("== Open-Meteo (Bengaluru centre) ==")
    w = get_weather(12.9716, 77.5946)
    hours = w.get("hourly", {})
    temps = hours.get("temperature_2m", [])
    rains = hours.get("precipitation", [])
    print(f"  hourly points: {len(temps)}")
    if temps:
        print(f"  temp range: {min(temps):.1f}C - {max(temps):.1f}C")
        print(f"  precip sum: {sum(rains):.1f} mm")

    print("\n== BTP advisories ==")
    adv = fetch_advisories(limit=10)
    if adv and "error" in adv[0]:
        print(f"  ERROR: {adv[0]['error']}")
    else:
        print(f"  rows: {len(adv)}")
        for i, a in enumerate(adv[:3]):
            print(f"  [{i}] {a['row'][:3]}")

    print("\n== GDELT (Karnataka protest/traffic, 1 day) ==")
    g = search_events("Karnataka (protest OR traffic OR roadblock)", maxrecords=10, timespan="1d")
    arts = g.get("articles", [])
    if "error" in g:
        print(f"  ERROR: {g['error']}")
    print(f"  articles: {len(arts)}")
    for a in arts[:3]:
        print(f"  - {a.get('title', '?')[:90]}  ({a.get('domain', '')})")

    print("\n== data.gov.in ==")
    dg = query_resource("placeholder-resource-id", limit=5)
    if "warning" in dg:
        print(f"  {dg['warning']}")
    else:
        print(f"  records: {len(dg.get('records', []))}")


if __name__ == "__main__":
    main()
