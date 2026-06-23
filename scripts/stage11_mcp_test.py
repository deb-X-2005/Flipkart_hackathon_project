"""Stage 11: in-process smoke test of MCP tools (bypasses stdio transport).

Verifies each tool registers and runs end-to-end. The actual MCP server is
launched with: python -m src.mcp_server.server
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

import asyncio

from src.mcp_server.server import mcp, forecast_closure, plan_resources, forecast_and_plan, retrieve_similar_events, get_weather, get_news


async def list_tools():
    tools = await mcp.list_tools()
    return tools


def main() -> None:
    print("== Registered MCP tools ==")
    tools = asyncio.run(list_tools())
    for t in tools:
        print(f"  - {t.name:28} {t.description.splitlines()[0] if t.description else ''}")

    print("\n== forecast_closure (VIP movement on Mysore Road, 18:00) ==")
    r = forecast_closure(event_cause="vip_movement", corridor="Mysore Road",
                         hour=18, dow=2, month=6)
    print(f"  {r}")

    print("\n== plan_resources (use the closure_prob above) ==")
    p = plan_resources(event_cause="vip_movement", closure_prob=r["closure_prob"],
                       hour=18, corridor="Mysore Road")
    print(f"  {p}")

    print("\n== forecast_and_plan (one-shot, construction on Bellary Road, 09:00) ==")
    fp = forecast_and_plan(event_cause="construction", corridor="Bellary Road 1", hour=9)
    print(f"  closure_prob: {fp['closure_prob']}  severity: {fp['severity_score']}")
    print(f"  crowd: {fp['expected_crowd']}  barricades: {fp['barricades_needed']}  officers: {fp['officers_needed']}")
    print(f"  divert to: {fp['diversion_corridor']}")

    print("\n== retrieve_similar_events ==")
    for r in retrieve_similar_events("water logging during monsoon", k=3):
        label = r.get("title") or f"{r.get('event_cause')} @ {r.get('corridor')}"
        print(f"  [{r.get('kind','?')}] score={r['score']:.3f}  {str(label)[:80]}")

    print("\n== get_weather (Bengaluru centre) ==")
    w = get_weather(12.97, 77.59, hours=3)
    print(f"  hourly points: {len(w.get('hourly',{}).get('temperature_2m', []))}")

    print("\n== get_news ==")
    n = get_news("Bangalore traffic", limit=3)
    for a in n:
        print(f"  [{a.get('source','?'):28}] {a['title'][:80]}")


if __name__ == "__main__":
    main()
