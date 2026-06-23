"""Tiny SQLite-backed cache with TTL. Used by all real-time data sources."""
import hashlib
import json
import sqlite3
import time
from pathlib import Path

from src.config import ROOT

DB = ROOT / "data" / "cache.sqlite"


def _conn() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.execute(
        "CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY, expires INTEGER, value TEXT)"
    )
    return c


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def get(key: str):
    h = _hash(key)
    with _conn() as c:
        row = c.execute("SELECT expires, value FROM cache WHERE key = ?", (h,)).fetchone()
    if not row:
        return None
    expires, value = row
    if expires < time.time():
        return None
    return json.loads(value)


def put(key: str, value, ttl_seconds: int = 86400) -> None:
    h = _hash(key)
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO cache(key, expires, value) VALUES (?, ?, ?)",
            (h, int(time.time() + ttl_seconds), json.dumps(value, default=str)),
        )


def purge_expired() -> int:
    with _conn() as c:
        cur = c.execute("DELETE FROM cache WHERE expires < ?", (int(time.time()),))
        return cur.rowcount
