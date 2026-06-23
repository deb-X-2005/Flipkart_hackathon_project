"""Anthropic Claude client."""
import os
from functools import lru_cache


@lru_cache(maxsize=1)
def _client():
    from anthropic import Anthropic
    return Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))


def chat(prompt: str, model: str | None = None, system: str | None = None,
         temperature: float = 0.2, max_tokens: int = 1024) -> str:
    resp = _client().messages.create(
        model=model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        max_tokens=max_tokens,
        temperature=temperature,
        system=system or "",
        messages=[{"role": "user", "content": prompt}],
    )
    parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    return "\n".join(parts)
