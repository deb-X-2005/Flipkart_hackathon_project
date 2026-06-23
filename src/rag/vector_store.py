"""FAISS index wrapper: build, save, load. Uses inner-product (cosine on normalized embeds)."""
from pathlib import Path
import json
import numpy as np


def build(embeddings: np.ndarray):
    import faiss
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings.astype("float32"))
    return index


def save(index, metadata: list[dict], path: Path) -> None:
    import faiss
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(path))
    path.with_suffix(".meta.json").write_text(
        json.dumps(metadata, ensure_ascii=False, default=str), encoding="utf-8"
    )


def load(path: Path):
    import faiss
    path = Path(path)
    index = faiss.read_index(str(path))
    metadata = json.loads(path.with_suffix(".meta.json").read_text(encoding="utf-8"))
    return index, metadata
