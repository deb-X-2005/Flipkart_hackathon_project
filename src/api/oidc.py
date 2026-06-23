"""OIDC SSO scaffold. Google by default; configurable via env.

Required env:
  OIDC_PROVIDER       google | microsoft | custom
  OIDC_CLIENT_ID
  OIDC_CLIENT_SECRET
  OIDC_REDIRECT_URI   e.g. https://traffic.example.gov.in/api/auth/oidc/callback
  OIDC_AUTHORIZED_DOMAIN  optional, e.g. "btp.karnataka.gov.in" to whitelist email domain
  OIDC_DEFAULT_ROLE   role given on first login (default: viewer)

When OIDC_PROVIDER is unset, these routes 404 — demo /auth/login still works.
"""
import os
from urllib.parse import urlencode

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from src.security.auth import issue, DEFAULT_TTL
from src.security.audit import log as audit_log
from src.security.secrets import get_secret

router = APIRouter(prefix="/auth/oidc", tags=["oidc"])

CONF = {
    "google": {
        "server_metadata_url": "https://accounts.google.com/.well-known/openid-configuration",
        "client_kwargs": {"scope": "openid email profile"},
    },
    "microsoft": {
        "server_metadata_url": "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
        "client_kwargs": {"scope": "openid email profile"},
    },
}

oauth = OAuth()
_provider = os.getenv("OIDC_PROVIDER", "").lower()
if _provider in CONF:
    oauth.register(
        name=_provider,
        client_id=get_secret("OIDC_CLIENT_ID"),
        client_secret=get_secret("OIDC_CLIENT_SECRET"),
        **CONF[_provider],
    )


def install_session_middleware(app, secret: str) -> None:
    """Call once at app startup with a stable secret."""
    app.add_middleware(SessionMiddleware, secret_key=secret, same_site="lax", https_only=False)


@router.get("/login")
async def oidc_login(request: Request):
    if not _provider or _provider not in CONF:
        raise HTTPException(404, "OIDC not configured")
    client = getattr(oauth, _provider)
    redirect_uri = os.getenv("OIDC_REDIRECT_URI", str(request.url_for("oidc_callback")))
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def oidc_callback(request: Request):
    if not _provider or _provider not in CONF:
        raise HTTPException(404, "OIDC not configured")
    client = getattr(oauth, _provider)
    token = await client.authorize_access_token(request)
    info = token.get("userinfo") or await client.userinfo(token=token)
    email = info.get("email") or info.get("preferred_username") or ""
    if not email:
        audit_log("oidc.no_email", outcome="fail", info=str(info)[:200])
        raise HTTPException(400, "no email in OIDC response")

    allowed = os.getenv("OIDC_AUTHORIZED_DOMAIN", "")
    if allowed and not email.lower().endswith("@" + allowed.lower()):
        audit_log("oidc.domain_reject", actor=email, outcome="fail", required_domain=allowed)
        raise HTTPException(403, f"email domain not in {allowed}")

    role = os.getenv("OIDC_DEFAULT_ROLE", "viewer")
    jwt_tok = issue(email, role=role, ttl=DEFAULT_TTL)
    audit_log("oidc.login_ok", actor=email, role=role, provider=_provider)
    # Hand the JWT to the SPA via fragment (keeps it out of server access logs)
    frontend = os.getenv("FRONTEND_ORIGIN", "/")
    return RedirectResponse(url=f"{frontend}#token={jwt_tok}&role={role}")
