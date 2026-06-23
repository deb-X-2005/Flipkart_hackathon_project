"""Shared test fixtures + env."""
import os

# Set BEFORE any imports of src.security.* that read env at import time
os.environ.setdefault("AUTH_SECRET", "test-secret-with-at-least-32-bytes-of-entropy-okay")

import pytest


@pytest.fixture
def crypto_env():
    from src.security.crypto import generate_key, _cipher
    os.environ["CRYPTO_KEY"] = generate_key()
    _cipher.cache_clear()
    yield


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    from src.data import cache
    monkeypatch.setattr(cache, "DB", tmp_path / "test.sqlite")
    yield cache


@pytest.fixture
def isolated_audit(tmp_path, monkeypatch):
    from src.security import audit
    monkeypatch.setattr(audit, "LOG_DIR", tmp_path)
    yield audit
