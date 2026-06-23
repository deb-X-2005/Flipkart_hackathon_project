import pytest
from src.config import ROOT

INDEX = ROOT / "data" / "rag" / "events.faiss"
if not INDEX.exists():
    pytest.skip("FAISS index not built; run scripts/stage9_build_rag.py", allow_module_level=True)

from src.rag.retriever import retrieve


def test_retrieve_returns_at_most_k():
    r = retrieve("water logging", k=3)
    assert 0 < len(r) <= 3
    assert all("score" in x for x in r)


def test_scores_descending():
    r = retrieve("VIP convoy on Mysore Road", k=5)
    scores = [x["score"] for x in r]
    assert scores == sorted(scores, reverse=True)


def test_relevant_top_hit_for_obvious_query():
    r = retrieve("water logging during monsoon", k=3)
    causes = [x.get("event_cause") for x in r if x.get("kind") == "event"]
    assert "water_logging" in causes
