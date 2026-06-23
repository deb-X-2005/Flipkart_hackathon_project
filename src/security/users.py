"""Tiny local user store. Bcrypt-hashed passwords. Seeded with demo accounts on first run.

Production: replace with SSO/OIDC (already scaffolded in src/api/oidc.py) or LDAP.
"""
import json
from pathlib import Path
import bcrypt

from src.config import ROOT

DB = ROOT / "data" / "users.json"
ROLES = {"viewer", "operator", "admin"}

DEFAULT_USERS = [
    {"username": "viewer",   "password": "viewer123",   "role": "viewer"},
    {"username": "operator", "password": "operator123", "role": "operator"},
    {"username": "admin",    "password": "admin123",    "role": "admin"},
]


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8")[:72], bcrypt.gensalt()).decode("ascii")


def _verify(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8")[:72], hashed.encode("ascii"))
    except Exception:
        return False


def _load() -> list[dict]:
    if DB.exists():
        return json.loads(DB.read_text(encoding="utf-8"))
    DB.parent.mkdir(parents=True, exist_ok=True)
    seeded = [
        {"username": u["username"], "role": u["role"], "password_hash": _hash(u["password"])}
        for u in DEFAULT_USERS
    ]
    DB.write_text(json.dumps(seeded, indent=2), encoding="utf-8")
    return seeded


def authenticate(username: str, password: str) -> str | None:
    users = _load()
    for u in users:
        if u["username"] == username and _verify(password, u["password_hash"]):
            return u["role"]
    return None


def create(username: str, password: str, role: str = "viewer") -> bool:
    """Add a new account. Returns False if username taken or invalid."""
    if not username or not password or len(password) < 8:
        return False
    if role not in ROLES:
        return False
    users = _load()
    if any(u["username"] == username for u in users):
        return False
    users.append({"username": username, "role": role, "password_hash": _hash(password)})
    DB.write_text(json.dumps(users, indent=2), encoding="utf-8")
    return True


def list_demo_users() -> list[dict]:
    """Public summary for the login screen (NEVER includes hash)."""
    return [{"username": u["username"], "password": u["password"], "role": u["role"]} for u in DEFAULT_USERS]
