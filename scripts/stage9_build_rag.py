"""Stage 9: build FAISS index over events (+ optional recent news/reddit).
Saves to data/rag/events.faiss and .meta.json. Runs a few demo queries.
"""
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.config import DATA_PROCESSED, ROOT
from src.rag import embeddings, vector_store
from src.rag.retriever import INDEX_PATH, retrieve
from src.data.sources.reddit import search as reddit_search
from src.data.sources.news import search as news_search


def _event_doc(r: pd.Series) -> str:
    parts = [
        str(r.get("event_type", "")),
        str(r.get("event_cause", "")),
        f"on {str(r.get('start_datetime', ''))[:10]}",
        f"at {r.get('address') or r.get('corridor') or 'unknown location'}",
    ]
    desc = r.get("description")
    if isinstance(desc, str) and desc.strip():
        parts.append(desc[:300])
    if r.get("requires_road_closure"):
        parts.append("required road closure")
    if "severity_score" in r and pd.notna(r["severity_score"]):
        parts.append(f"severity {float(r['severity_score']):.2f}")
    return ". ".join(p for p in parts if p)


def _build_docs() -> tuple[list[str], list[dict]]:
    df = pd.read_csv(DATA_PROCESSED / "events_with_plan.csv")
    docs = [_event_doc(r) for _, r in df.iterrows()]
    meta = [
        {
            "kind": "event",
            "id": str(r.get("id", "")),
            "event_cause": r.get("event_cause"),
            "corridor": r.get("corridor"),
            "address": r.get("address"),
            "start_datetime": str(r.get("start_datetime", ""))[:19],
            "severity": float(r["severity_score"]) if pd.notna(r.get("severity_score")) else None,
        }
        for _, r in df.iterrows()
    ]

    for q in ["Bangalore traffic", "Karnataka protest", "Bengaluru roadblock OR diversion"]:
        for h in reddit_search(q, limit_each=15, timespan_days=14):
            docs.append(f"reddit/{h['subreddit']}: {h['title']}. {h['summary']}")
            meta.append({"kind": "reddit", "subreddit": h["subreddit"], "url": h.get("link"), "title": h["title"]})
        for n in news_search(q, limit=10):
            docs.append(f"news: {n['title']}. {n.get('summary','')}")
            meta.append({"kind": "news", "source": n.get("source"), "url": n.get("link"), "title": n["title"]})

    return docs, meta


def main() -> None:
    print("building corpus...")
    docs, meta = _build_docs()
    print(f"  total docs: {len(docs):,}  (events + reddit + news)")

    print("embedding (may take ~1 min on CPU)...")
    embs = embeddings.embed(docs, batch_size=128)
    print(f"  shape: {embs.shape}")

    index = vector_store.build(embs)
    vector_store.save(index, meta, INDEX_PATH)
    print(f"  saved -> {INDEX_PATH}")

    print("\n== demo queries ==")
    for q in ["VIP convoy on Mysore Road", "monsoon water logging", "construction blocking Bellary Road", "protest near Vidhana Soudha"]:
        print(f"\nq: {q}")
        for r in retrieve(q, k=3):
            kind = r.get("kind", "?")
            label = r.get("title") or f"{r.get('event_cause')} @ {r.get('corridor') or r.get('address') or '-'}"
            print(f"  [{kind:6}] score={r['score']:.3f}  {str(label)[:90]}")


if __name__ == "__main__":
    main()
