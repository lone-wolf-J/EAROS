"""EAROS authentication, tenancy assignment, and server-managed sessions.

This module is deliberately conservative: identity is verified by the configured
upstream session service, tenant and role assignments are explicit, and only
hashes of EAROS session tokens are persisted.
"""
from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Cookie, Header, HTTPException, Request, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, ConfigDict, Field

from foundation import Role, new_user_id, utcnow_iso

SESSION_TTL_DAYS = int(os.getenv("EAROS_SESSION_TTL_DAYS", "7"))
DEMONSTRATION_SESSION_DATA_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
LOG = logging.getLogger("earos.auth")
VALID_ROLES = {item.value for item in Role}


def _env_flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _is_production() -> bool:
    return os.getenv("EAROS_ENV", "development").strip().lower() == "production"


def _configured_session_data_url() -> str:
    """Return a validated identity-session endpoint without trusting demo defaults in production."""
    configured = os.getenv("AUTH_SESSION_DATA_URL", "").strip()
    if not configured:
        if _is_production():
            raise RuntimeError("AUTH_SESSION_DATA_URL must be explicitly configured in production")
        return DEMONSTRATION_SESSION_DATA_URL
    parsed = urlparse(configured)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeError("AUTH_SESSION_DATA_URL must be an absolute HTTPS endpoint without credentials, query, or fragment")
    if _is_production() and configured == DEMONSTRATION_SESSION_DATA_URL:
        raise RuntimeError("AUTH_SESSION_DATA_URL must not use the demonstration identity service in production")
    return configured


def validate_production_auth_configuration() -> None:
    """Fail application startup when production identity or developer-access controls are unsafe."""
    if not _is_production():
        return
    _configured_session_data_url()
    if _env_flag("EAROS_ENABLE_DEV_LOGIN", False):
        raise RuntimeError("EAROS_ENABLE_DEV_LOGIN must be disabled in production")


def _session_digest(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def _cookie_settings() -> dict[str, object]:
    same_site = os.getenv("EAROS_COOKIE_SAMESITE", "lax").strip().lower()
    if same_site not in {"lax", "strict", "none"}:
        raise RuntimeError("EAROS_COOKIE_SAMESITE must be lax, strict, or none")
    if same_site == "none" and not _env_flag("EAROS_COOKIE_SECURE", True):
        raise RuntimeError("SameSite=None requires EAROS_COOKIE_SECURE=true")
    return {
        "path": "/",
        "httponly": True,
        "secure": _env_flag("EAROS_COOKIE_SECURE", True),
        "samesite": same_site,
        "max_age": SESSION_TTL_DAYS * 24 * 60 * 60,
    }


def _parse_expiry(value: str | datetime) -> datetime:
    expiry = datetime.fromisoformat(value) if isinstance(value, str) else value
    return expiry.replace(tzinfo=timezone.utc) if expiry.tzinfo is None else expiry


class AppUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    role: str = Role.RECRUITER.value
    organization_id: str
    created_at: str = Field(default_factory=utcnow_iso)


async def _read_session_user(db: AsyncIOMotorDatabase, token: str) -> Optional[AppUser]:
    session = await db.user_sessions.find_one({"session_token_hash": _session_digest(token)}, {"_id": 0})
    if not session or _parse_expiry(session["expires_at"]) <= datetime.now(timezone.utc):
        return None
    user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    return AppUser(**user_doc) if user_doc else None


async def _create_session(db: AsyncIOMotorDatabase, user: AppUser, request: Request) -> str:
    token = secrets.token_urlsafe(48)
    await db.user_sessions.insert_one({
        "user_id": user.user_id,
        "organization_id": user.organization_id,
        "session_token_hash": _session_digest(token),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)).isoformat(),
        "created_at": utcnow_iso(),
        "user_agent": request.headers.get("user-agent", "")[:512],
    })
    return token


async def _provision_or_update_user(db: AsyncIOMotorDatabase, identity: dict) -> AppUser:
    email = str(identity["email"]).strip().lower()
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        await db.users.update_one(
            {"email": email},
            {"$set": {"name": identity.get("name") or existing.get("name", email), "picture": identity.get("picture") or existing.get("picture")}},
        )
        return AppUser(**{**existing, "name": identity.get("name") or existing.get("name", email), "picture": identity.get("picture") or existing.get("picture")})

    if not _env_flag("EAROS_ALLOW_JIT_PROVISIONING", False):
        raise HTTPException(status_code=403, detail="User provisioning is disabled. Ask an EAROS administrator for access.")
    organization_id = identity.get("organization_id") or identity.get("organizationId") or os.getenv("EAROS_DEFAULT_ORGANIZATION_ID")
    if not organization_id:
        raise HTTPException(status_code=422, detail="Authenticated identity is missing an organization assignment.")
    # JIT identities start at the least-privileged staffing role. Administrators
    # assign elevated roles through governed member administration after provisioning.
    user = AppUser(user_id=new_user_id(), email=email, name=identity.get("name") or email, picture=identity.get("picture"), role=Role.RECRUITER.value, organization_id=str(organization_id))
    await db.users.insert_one(user.model_dump())
    await db.audit_events.insert_one({"event_type": "identity.user_provisioned", "organization_id": user.organization_id, "actor_user_id": user.user_id, "created_at": utcnow_iso(), "metadata": {"role": user.role}})
    return user


def build_router(db: AsyncIOMotorDatabase) -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    @router.post("/session")
    async def create_session(request: Request, response: Response, x_session_id: str = Header(..., alias="X-Session-ID")):
        """Exchange a validated upstream session for an EAROS-only secure cookie."""
        if len(x_session_id.strip()) < 8:
            raise HTTPException(status_code=401, detail="Invalid upstream session identifier")
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
                upstream = await client.get(_configured_session_data_url(), headers={"X-Session-ID": x_session_id})
        except httpx.HTTPError as exc:
            LOG.exception("Configured identity service was unavailable")
            raise HTTPException(status_code=502, detail="Configured identity service is unavailable") from exc
        if upstream.status_code != 200:
            LOG.warning("Identity service rejected a session: status=%s", upstream.status_code)
            raise HTTPException(status_code=401, detail="Invalid authenticated session")
        try:
            identity = upstream.json()
        except ValueError as exc:
            raise HTTPException(status_code=502, detail="Configured identity service returned malformed data") from exc
        if not identity.get("email"):
            raise HTTPException(status_code=422, detail="Authenticated identity is missing an email address")
        user = await _provision_or_update_user(db, identity)
        token = await _create_session(db, user, request)
        response.set_cookie(key="session_token", value=token, **_cookie_settings())
        return {"ok": True, "user": user.model_dump()}

    @router.get("/me")
    async def me(session_token_cookie: Optional[str] = Cookie(default=None, alias="session_token"), authorization: Optional[str] = Header(default=None)):
        token = session_token_cookie or (authorization.split(None, 1)[1].strip() if authorization and authorization.lower().startswith("bearer ") else None)
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user = await _read_session_user(db, token)
        if not user:
            raise HTTPException(status_code=401, detail="Session expired or invalid")
        return user.model_dump()

    @router.post("/logout")
    async def logout(response: Response, session_token_cookie: Optional[str] = Cookie(default=None, alias="session_token")):
        if session_token_cookie:
            await db.user_sessions.delete_one({"session_token_hash": _session_digest(session_token_cookie)})
        response.delete_cookie("session_token", path="/")
        return {"ok": True}

    @router.post("/dev-login", include_in_schema=False)
    async def dev_login(request: Request, response: Response, email: str):
        """Development-only login. It is unreachable unless explicitly enabled."""
        if _is_production() or not _env_flag("EAROS_ENABLE_DEV_LOGIN", False):
            raise HTTPException(status_code=404, detail="Not found")
        identity = {"email": email, "name": email, "organization_id": os.getenv("EAROS_DEFAULT_ORGANIZATION_ID"), "role": Role.RECRUITER.value}
        user = await _provision_or_update_user(db, identity)
        token = await _create_session(db, user, request)
        response.set_cookie(key="session_token", value=token, **_cookie_settings())
        return {"ok": True, "user": user.model_dump()}

    return router


async def get_current_user(request: Request, db: AsyncIOMotorDatabase) -> AppUser:
    token = request.cookies.get("session_token")
    authorization = request.headers.get("authorization", "")
    if not token and authorization.lower().startswith("bearer "):
        token = authorization.split(None, 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = await _read_session_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return user
