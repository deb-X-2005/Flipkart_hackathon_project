"""Structured JSON audit logger. ISO 27001 A.12.4 + GDPR Art 30 (records of processing).

Every entry is one JSON line on disk + emitted to stdlib logger.
Logs are append-only; rotated by date.
"""
import json
import logging
import os
import socket
import time
from datetime import datetime, timezone
from pathlib import Path

from src.config import ROOT

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
HOST = socket.gethostname()
_logger = logging.getLogger("audit")
_logger.setLevel(logging.INFO)
_logger.propagate = False
if os.getenv("AUDIT_STDOUT") == "1" and not _logger.handlers:
    _logger.addHandler(logging.StreamHandler())


def _today_log() -> Path:
    return LOG_DIR / f"audit-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"


def log(action: str, *, actor: str = "system", resource: str = "", outcome: str = "ok", **fields) -> None:
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "host": HOST,
        "pid": os.getpid(),
        "actor": actor,
        "action": action,
        "resource": resource,
        "outcome": outcome,
        **fields,
    }
    line = json.dumps(rec, ensure_ascii=False, default=str)
    with _today_log().open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    _logger.info("AUDIT %s", line)


def tail(n: int = 20, path: Path | None = None) -> list[dict]:
    p = path or _today_log()
    if not p.exists():
        return []
    lines = p.read_text(encoding="utf-8").splitlines()[-n:]
    return [json.loads(ln) for ln in lines if ln.strip()]
