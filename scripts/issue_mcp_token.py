"""Admin CLI: issue an MCP token for an AI agent.

Usage:
  python scripts/issue_mcp_token.py <agent_id> [--scopes forecast,plan,rag,...] [--ttl 86400]
  python scripts/issue_mcp_token.py my-agent --scopes forecast,plan
"""
from pathlib import Path
import argparse
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Ensure AUTH_SECRET exists for the demo; in prod it's loaded from .env
os.environ.setdefault("AUTH_SECRET", "dev-only-replace-me-with-token_urlsafe-48")

from src.security.auth import issue_mcp_token, MCP_TTL


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("agent_id")
    ap.add_argument("--scopes", default="forecast,plan,rag,weather,news,reddit",
                    help="comma-separated tool scopes")
    ap.add_argument("--ttl", type=int, default=MCP_TTL, help="seconds")
    args = ap.parse_args()
    scopes = [s.strip() for s in args.scopes.split(",") if s.strip()]
    token = issue_mcp_token(args.agent_id, scopes, ttl=args.ttl)
    print(token)
    print(f"\n(give this to the agent; ttl={args.ttl}s, scopes={scopes})", file=sys.stderr)


if __name__ == "__main__":
    main()
