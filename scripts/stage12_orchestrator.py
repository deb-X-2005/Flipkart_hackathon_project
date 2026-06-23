"""Stage 12 demo: natural-language traffic queries -> full briefing.

Uses Ollama by default (qwen3:1.7b). Override via LLM_MODE env var.
"""
from pathlib import Path
import os
import sys
import logging

os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
logging.disable(logging.WARNING)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
from src.agents.orchestrator import handle
from src.llm.client import resolved_mode

QUERIES = [
    "Cricket match at Chinnaswamy Stadium tomorrow evening — expect heavy crowd",
    "Tree fell on Bellary Road this morning blocking one lane",
    "VIP convoy from airport to MG Road around 6pm Friday",
]


def main() -> None:
    print(f"LLM backend: {resolved_mode()}")
    for q in QUERIES:
        print(f"\n========================================\n> {q}\n========================================")
        out = handle(q)
        print(f"\nextracted: {json.dumps(out['extracted'], indent=2)}")
        print(f"\nforecast:  closure_prob = {out['forecast']['closure_prob']}")
        p = out["plan"]
        print(f"plan:      crowd={p['expected_crowd']:,}  officers={p['officers_needed']}  barricades={p['barricades_needed']}")
        print(f"           severity={p['severity_score']}  divert to {p['diversion_corridor']}")
        print(f"\nbriefing:\n{out['briefing']}\n")


if __name__ == "__main__":
    main()
