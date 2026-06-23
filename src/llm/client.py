"""Unified run_llm() with backend switching.

LLM_MODE selects backend: ollama | openai | anthropic | openrouter
If LLM_MODE is unset: auto-detect. Prefer Ollama if running locally; else error.
"""
import os

from src.llm import ollama as _ollama
from src.security.audit import log as audit_log


def resolved_mode() -> str:
    explicit = os.getenv("LLM_MODE", "").strip().lower()
    if explicit:
        return explicit
    if _ollama.health():
        return "ollama"
    raise RuntimeError("LLM_MODE not set and Ollama not reachable. Set LLM_MODE=openai|anthropic|openrouter or start Ollama.")


def run_llm(prompt: str, system: str | None = None, temperature: float = 0.2, model: str | None = None) -> str:
    mode = resolved_mode()
    audit_log("llm.call", actor="system", resource=f"mode:{mode}", prompt_chars=len(prompt))
    if mode == "ollama":
        return _ollama.chat(prompt, model=model, system=system, temperature=temperature)
    if mode == "openai":
        from src.llm.openai_client import chat
        return chat(prompt, provider="openai", model=model, system=system, temperature=temperature)
    if mode == "anthropic":
        from src.llm.anthropic_client import chat
        return chat(prompt, model=model, system=system, temperature=temperature)
    if mode == "openrouter":
        from src.llm.openai_client import chat
        return chat(prompt, provider="openrouter", model=model, system=system, temperature=temperature)
    raise ValueError(f"unknown LLM_MODE: {mode}")
