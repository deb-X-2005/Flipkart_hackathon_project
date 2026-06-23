"""FastAPI Bearer token auth + RBAC. ISO 27001 A.9 (access control).

Tokens are JWT-HS256, signed by AUTH_SECRET env var. Three roles:
  admin    - all actions, including erasure
  operator - run forecasts, view all data
  viewer   - read-only, no PII fields

Wire in api/main.py via:
    @app.get("/x", dependencies=[Depends(require_role("operator"))])
"""
import os
import time
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.security.audit import log as audit_log

ALG = "HS256"
DEFAULT_TTL = 3600  # 1 hour for humans
MCP_TTL = 86400     # 1 day for agents
API_AUD = "api"     # humans via FastAPI
MCP_AUD = "mcp"     # AI agents via MCP server


def _secret() -> str:
    from src.security.secrets import get_secret
    s = get_secret("AUTH_SECRET")
    if not s:
        raise RuntimeError("AUTH_SECRET not set; refusing to issue/verify tokens")
    return s


def issue(subject: str, role: str, ttl: int = DEFAULT_TTL) -> str:
    """Human JWT: aud=api, role in {viewer, operator, admin}."""
    now = int(time.time())
    payload = {"sub": subject, "role": role, "aud": API_AUD, "iat": now, "exp": now + ttl}
    token = jwt.encode(payload, _secret(), algorithm=ALG)
    audit_log("auth.issue", actor=subject, role=role, ttl=ttl, aud=API_AUD)
    return token


def issue_mcp_token(agent_id: str, scopes: list[str], ttl: int = MCP_TTL) -> str:
    """Agent MCP token: aud=mcp, role=mcp_agent, plus scoped tool whitelist."""
    now = int(time.time())
    payload = {
        "sub": agent_id, "role": "mcp_agent", "scopes": scopes,
        "aud": MCP_AUD, "iat": now, "exp": now + ttl,
    }
    token = jwt.encode(payload, _secret(), algorithm=ALG)
    audit_log("auth.issue_mcp", actor=agent_id, scopes=scopes, ttl=ttl, aud=MCP_AUD)
    return token


def verify(token: str) -> dict:
    return jwt.decode(token, _secret(), algorithms=[ALG], audience=API_AUD)


def verify_mcp_token(token: str) -> dict:
    return jwt.decode(token, _secret(), algorithms=[ALG], audience=MCP_AUD)


def verify_any(token: str) -> dict:
    """Accept either kind. Returns claims (includes 'aud' so the caller knows)."""
    for aud in (MCP_AUD, API_AUD):
        try:
            return jwt.decode(token, _secret(), algorithms=[ALG], audience=aud)
        except jwt.InvalidAudienceError:
            continue
    raise jwt.InvalidTokenError("audience matches neither api nor mcp")


bearer = HTTPBearer(auto_error=False)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    try:
        return verify(creds.credentials)
    except jwt.PyJWTError as e:
        audit_log("auth.reject", outcome="fail", reason=str(e))
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")


ROLE_RANK = {"viewer": 0, "operator": 1, "admin": 2}


def require_role(minimum: str):
    def _dep(user: dict = Depends(current_user)) -> dict:
        if ROLE_RANK.get(user.get("role"), -1) < ROLE_RANK.get(minimum, 99):
            audit_log("auth.forbid", actor=user.get("sub"), required=minimum, had=user.get("role"), outcome="fail")
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"role >= {minimum} required")
        return user
    return _dep
