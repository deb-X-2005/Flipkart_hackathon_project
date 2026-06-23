"""Ollama HTTP client. Local inference; no API key needed.
Talks to http://localhost:11434 by default (override via OLLAMA_HOST env).
"""
import json
import os
from typing import Iterator

import requests

HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")


def health() -> bool:
    try:
        r = requests.get(f"{HOST}/api/tags", timeout=2)
        return r.status_code == 200
    except requests.RequestException:
        return False


def list_local() -> list[dict]:
    r = requests.get(f"{HOST}/api/tags", timeout=5)
    r.raise_for_status()
    return r.json().get("models", [])


def chat(prompt: str, model: str | None = None, system: str | None = None, temperature: float = 0.2) -> str:
    body = {
        "model": model or DEFAULT_MODEL,
        "messages": ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "options": {"temperature": temperature},
    }
    r = requests.post(f"{HOST}/api/chat", json=body, timeout=120)
    r.raise_for_status()
    return r.json()["message"]["content"]


def pull(model: str) -> Iterator[dict]:
    """Stream pull progress. Yields {'status': ..., 'completed': ..., 'total': ...}."""
    with requests.post(f"{HOST}/api/pull", json={"model": model, "stream": True},
                       stream=True, timeout=None) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def search_library(query: str, limit: int = 10) -> list[dict]:
    """Best-effort search of ollama.com/library. Falls back to curated list on failure."""
    url = "https://ollama.com/library"
    try:
        from bs4 import BeautifulSoup
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        q = query.lower()
        for a in soup.select('a[href^="/library/"]'):
            name = a.get("href", "").removeprefix("/library/")
            desc = a.get_text(" ", strip=True)[:200]
            if not name:
                continue
            if q and q not in name.lower() and q not in desc.lower():
                continue
            items.append({"name": name, "description": desc})
            if len(items) >= limit:
                break
        if items:
            return items
    except Exception:
        pass
    # Fallback: curated popular models
    curated = [
        {"name": "llama3.2:3b", "description": "Meta Llama 3.2 (3B) — small, fast"},
        {"name": "llama3.1:8b", "description": "Meta Llama 3.1 (8B) — balanced"},
        {"name": "qwen2.5:7b", "description": "Alibaba Qwen 2.5 (7B) — strong instruction following"},
        {"name": "qwen3:1.7b", "description": "Alibaba Qwen 3 (1.7B) — tools + thinking"},
        {"name": "mistral:7b", "description": "Mistral 7B — general purpose"},
        {"name": "phi3:3.8b", "description": "Microsoft Phi-3 — small reasoning"},
        {"name": "gemma2:2b", "description": "Google Gemma 2 (2B) — efficient"},
        {"name": "nomic-embed-text", "description": "Nomic embedding model"},
    ]
    if query:
        q = query.lower()
        return [c for c in curated if q in c["name"].lower() or q in c["description"].lower()][:limit]
    return curated[:limit]
