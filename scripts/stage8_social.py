"""Stage 8: pull Reddit + Google News RSS for traffic / event chatter."""
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.sources.reddit import search as reddit_search
from src.data.sources.news import search as news_search

QUERIES = [
    "Bangalore traffic",
    "Karnataka protest",
    "Bengaluru roadblock OR diversion",
]


def main() -> None:
    print("== Reddit (r/bangalore, r/karnataka, r/india, r/IndiaSpeaks) ==")
    for q in QUERIES:
        hits = reddit_search(q, limit_each=25, timespan_days=14)
        print(f"\n  query: {q!r}  -> {len(hits)} posts")
        for h in hits[:3]:
            print(f"    [{h['subreddit']:14}] {h['title'][:90]}")

    print("\n\n== Google News RSS (India, last 24h+) ==")
    for q in QUERIES:
        items = news_search(q, limit=15)
        print(f"\n  query: {q!r}  -> {len(items)} articles")
        for i in items[:3]:
            print(f"    [{i.get('source','?'):30}] {i['title'][:90]}")


if __name__ == "__main__":
    main()
