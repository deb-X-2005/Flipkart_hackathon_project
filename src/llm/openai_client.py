"""OpenAI client + OpenRouter (same SDK, different base_url).

LLM_MODE=openai     -> api.openai.com
LLM_MODE=openrouter -> openrouter.ai/api/v1
"""
import os
from functools import lru_cache


@lru_cache(maxsize=2)
def _client(provider: str):
    from openai import OpenAI
    if provider == "openrouter":
        return OpenAI(api_key=os.getenv("OPENROUTER_API_KEY", ""),
                      base_url="https://openrouter.ai/api/v1")
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


def chat(prompt: str, provider: str = "openai", model: str | None = None,
         system: str | None = None, temperature: float = 0.2,
         max_tokens: int = 1024) -> str:
    """OpenAI / OpenRouter chat completion.
    max_tokens defaults to 1024 — briefings are short, and OpenRouter reserves
    credits up-front based on this value (uncapped = the model's max).
    """
    cli = _client(provider)
    default_model = "gpt-4o-mini" if provider == "openai" else "anthropic/claude-sonnet-4.5"
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": prompt}]
    resp = cli.chat.completions.create(
        model=model or os.getenv(f"{provider.upper()}_MODEL", default_model),
        messages=msgs,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""
