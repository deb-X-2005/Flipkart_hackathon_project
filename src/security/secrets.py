"""Secret retrieval. Reads from env first, falls back to /run/secrets/<name>
(Docker Swarm / Kubernetes / Nomad mount style). ISO 27001 A.9.4.

Usage:
  from src.security.secrets import get_secret
  AUTH_SECRET = get_secret("AUTH_SECRET", required=True)
"""
import os
from functools import lru_cache
from pathlib import Path

SECRETS_DIR = Path(os.getenv("SECRETS_DIR", "/run/secrets"))


@lru_cache(maxsize=64)
def get_secret(name: str, required: bool = False, default: str | None = None) -> str | None:
    val = os.getenv(name)
    if val:
        return val
    path = SECRETS_DIR / name
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    except OSError:
        pass
    if required:
        raise RuntimeError(f"required secret {name} not found in env or {SECRETS_DIR}")
    return default
