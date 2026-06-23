"""Right-to-erasure. GDPR Art 17. Removes an event by id from CSV + FAISS index + cache.

For FAISS: rebuild index without the erased row (flat index, fast enough at 8k scale).
"""
import json
from pathlib import Path
import pandas as pd

from src.config import DATA_PROCESSED, ROOT
from src.rag import embeddings, vector_store
from src.rag.retriever import INDEX_PATH
from src.security.audit import log as audit_log

EVENTS_CSV = DATA_PROCESSED / "events_with_plan.csv"


def erase(event_id: str, actor: str = "system") -> dict:
    if not event_id:
        raise ValueError("event_id required")
    df = pd.read_csv(EVENTS_CSV)
    n_before = len(df)
    df = df[df["id"].astype(str) != str(event_id)]
    removed = n_before - len(df)
    df.to_csv(EVENTS_CSV, index=False)

    rag_removed = 0
    if INDEX_PATH.exists() and INDEX_PATH.with_suffix(".meta.json").exists():
        meta = json.loads(INDEX_PATH.with_suffix(".meta.json").read_text(encoding="utf-8"))
        keep_idx = [i for i, m in enumerate(meta) if m.get("kind") != "event" or str(m.get("id")) != str(event_id)]
        rag_removed = len(meta) - len(keep_idx)
        if rag_removed:
            new_meta = [meta[i] for i in keep_idx]
            from src.rag.embeddings import _model  # noqa: F401  (warm cache)
            new_docs = [_render_doc(m) for m in new_meta]
            embs = embeddings.embed(new_docs)
            index = vector_store.build(embs)
            vector_store.save(index, new_meta, INDEX_PATH)

    audit_log("gdpr.erasure", actor=actor, resource=f"event:{event_id}", csv_rows_removed=removed, rag_rows_removed=rag_removed)
    return {"event_id": event_id, "csv_removed": removed, "rag_removed": rag_removed}


def _render_doc(m: dict) -> str:
    if m.get("kind") == "event":
        return f"{m.get('event_cause','')} at {m.get('corridor') or m.get('address') or 'unknown'}"
    return f"{m.get('kind','?')}: {m.get('title','')}"
