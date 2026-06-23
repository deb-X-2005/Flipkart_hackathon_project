import pytest
from unittest.mock import patch

from src.config import ROOT

if not (ROOT / "models" / "closure_clf.cbm").exists():
    pytest.skip("model not trained", allow_module_level=True)
if not (ROOT / "data" / "rag" / "events.faiss").exists():
    pytest.skip("RAG index not built", allow_module_level=True)

EXTRACT_JSON = (
    '{"event_cause": "construction", "event_type": "unplanned", '
    '"corridor": "Bellary Road 1", "hour": 9, "is_weekend": 0, '
    '"latitude": 12.97, "longitude": 77.59}'
)
BRIEFING = "Construction on Bellary Road. Deploy officers. Divert traffic."


def fake_run_llm(prompt, system=None, **kw):
    return BRIEFING if "Briefing:" in prompt else EXTRACT_JSON


def test_handle_full_pipeline():
    with patch("src.agents.orchestrator.run_llm", side_effect=fake_run_llm):
        from src.agents.orchestrator import handle
        out = handle("Construction on Bellary Road at 9am")
    assert out["extracted"]["event_cause"] == "construction"
    assert 0.0 <= out["forecast"]["closure_prob"] <= 1.0
    assert out["plan"]["officers_needed"] >= 1
    assert out["plan"]["barricades_needed"] >= 1
    assert BRIEFING in out["briefing"]
