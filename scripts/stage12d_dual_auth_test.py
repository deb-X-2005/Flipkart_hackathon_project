"""Stage 12d: verify dual-auth (human JWT vs MCP agent token)."""
from pathlib import Path
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("AUTH_SECRET", "dev-only-replace-me-with-token_urlsafe-48")

from src.security.auth import (
    issue, issue_mcp_token, verify, verify_mcp_token, verify_any,
    API_AUD, MCP_AUD,
)


def section(t):
    print(f"\n=== {t} ===")


def main() -> None:
    section("Issue human JWT (aud=api)")
    human_tok = issue("alice@btp.gov.in", role="operator")
    print(f"  token: {human_tok[:50]}...")
    print(f"  claims: {verify(human_tok)}")

    section("Issue MCP agent token (aud=mcp)")
    agent_tok = issue_mcp_token("agent-research-bot", scopes=["forecast", "plan", "rag"], ttl=600)
    print(f"  token: {agent_tok[:50]}...")
    print(f"  claims: {verify_mcp_token(agent_tok)}")

    section("Cross-validation must FAIL")
    for desc, fn, tok in [
        ("human token via verify_mcp_token", verify_mcp_token, human_tok),
        ("agent token via verify (human)",   verify,           agent_tok),
    ]:
        try:
            fn(tok)
            print(f"  {desc}: SHOULD HAVE FAILED")
        except Exception as e:
            print(f"  {desc}: rejected ({type(e).__name__})")

    section("verify_any accepts either, reports aud")
    for tok in (human_tok, agent_tok):
        c = verify_any(tok)
        print(f"  sub={c['sub']:25} aud={c['aud']:3} role={c['role']}")


if __name__ == "__main__":
    main()
