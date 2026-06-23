"""Top-k retrieval over the FAISS index. Lazy-loaded singleton."""
from functools import lru_cache
from pathlib import Path

from src.config import ROOT
from src.rag import embeddings, vector_store

INDEX_PATH = ROOT / "data" / "rag" / "events.faiss"


@lru_cache(maxsize=1)
def _store():
    return vector_store.load(INDEX_PATH)


def retrieve(query: str, k: int = 5) -> list[dict]:
    index, meta = _store()
    q = embeddings.embed([query])
    D, I = index.search(q, k)
    results = []
    for score, idx in zip(D[0].tolist(), I[0].tolist()):
        if idx < 0 or idx >= len(meta):
            continue
        item = dict(meta[idx])
        item["score"] = round(float(score), 4)
        results.append(item)
    return results
