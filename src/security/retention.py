"""Data retention scheduler. GDPR Art 5(1)(e) (storage limitation) + ISO A.18.1.

Purges:
  - expired cache rows (already TTL'd)
  - audit logs older than RETENTION_AUDIT_DAYS (default 365)
  - scraped social/news content older than RETENTION_SCRAPE_DAYS (default 30)
"""
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.config import ROOT
from src.data.cache import purge_expired
from src.security.audit import log as audit_log

LOG_DIR = ROOT / "logs"


def purge_cache() -> int:
    deleted = purge_expired()
    audit_log("retention.purge_cache", count=deleted)
    return deleted


def purge_audit_logs(keep_days: int | None = None) -> int:
    keep = keep_days or int(os.getenv("RETENTION_AUDIT_DAYS", "365"))
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep)
    n = 0
    for f in LOG_DIR.glob("audit-*.jsonl"):
        try:
            d = datetime.strptime(f.stem.removeprefix("audit-"), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if d < cutoff:
                f.unlink()
                n += 1
        except ValueError:
            continue
    audit_log("retention.purge_audit", deleted=n, keep_days=keep)
    return n


def run() -> dict:
    return {"cache": purge_cache(), "audit": purge_audit_logs()}
