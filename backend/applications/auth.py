"""Emergent Google Auth — session cookie + Bearer fallback.

Implements /api/auth/session, /api/auth/me, /api/auth/logout.
Also assigns a role & organization to first-time users (defaults to recruiter@LevelShift).
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Cookie, Header, HTTPException, Request, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, ConfigDict, Field

from foundation import Role, new_user_id, utcnow_iso

AUTH_SESSION_DATA_URL = (
    "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
)
SESSION_TTL_DAYS = 7


class AppUser(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    role: str = Role.RECRUITER.value
    organization_id: str = "org_levelshift"
    created_at: str = Field(default_factory=utcnow_iso)


def build_router(db: AsyncIOMotorDatabase) -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    async def _resolve_role(email: str) -> str:
        email_l = email.lower()
        if any(x in email_l for x in ("exec", "ceo", "cfo", "cpo", "chro")):
            return Role.EXECUTIVE.value
        if any(x in email_l for x in ("manager", "director", "vp", "head", "lead")):
            return Role.HIRING_MANAGER.value
        if "candidate" in email_l:
            return Role.CANDIDATE.value
        return Role.RECRUITER.value

    async def _upsert_user(payload: dict) -> AppUser:
        email = payload["email"]
        existing = await db.users.find_one({"email": email}, {"_id": 0})
        if existing:
            # keep the same user_id, refresh profile
            await db.users.update_one(
                {"email": email},
                {"$set": {
                    "name": payload.get("name", existing.get("name", "")),
                    "picture": payload.get("picture", existing.get("picture")),
                }},
            )
            return AppUser(**{**existing, "name": payload.get("name", existing.get("name", "")),
                              "picture": payload.get("picture", existing.get("picture"))})
        role = await _resolve_role(email)
        user = AppUser(
            user_id=new_user_id(),
            email=email,
            name=payload.get("name", email),
            picture=payload.get("picture"),
            role=role,
            organization_id="org_levelshift",
        )
        await db.users.insert_one(user.model_dump())
        return user

    async def _current_user_from_token(session_token: str) -> Optional[AppUser]:
        session = await db.user_sessions.find_one(
            {"session_token": session_token}, {"_id": 0}
        )
        if not session:
            return None
        expires_at = session["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            return None
        user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
        return AppUser(**user_doc) if user_doc else None

    @router.post("/session")
    async def create_session(
        response: Response,
        x_session_id: str = Header(..., alias="X-Session-ID"),
    ):
        """Exchange Emergent session_id for a persistent session_token cookie."""
        import logging
        log = logging.getLogger("earos.auth")
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    AUTH_SESSION_DATA_URL,
                    headers={"X-Session-ID": x_session_id},
                )
        except Exception as e:  # noqa: BLE001
            log.exception("Emergent auth backend unreachable: %s", e)
            raise HTTPException(
                status_code=502,
                detail=f"Emergent auth backend unreachable: {e.__class__.__name__}",
            )
        if resp.status_code != 200:
            log.warning(
                "Emergent session-data returned %s: %s",
                resp.status_code, resp.text[:200],
            )
            raise HTTPException(
                status_code=401,
                detail=f"Emergent session invalid ({resp.status_code})",
            )
        try:
            data = resp.json()
        except Exception as e:  # noqa: BLE001
            log.exception("Emergent session-data JSON parse failed")
            raise HTTPException(
                status_code=502,
                detail=f"Emergent session-data malformed: {e.__class__.__name__}",
            )
        if not data.get("email"):
            log.warning("Emergent session-data missing email: %s", str(data)[:200])
            raise HTTPException(
                status_code=422,
                detail="Emergent session-data missing email",
            )
        user = await _upsert_user(data)
        session_token = data.get("session_token") or f"tok_{os.urandom(24).hex()}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
        await db.user_sessions.insert_one({
            "user_id": user.user_id,
            "session_token": session_token,
            "expires_at": expires_at.isoformat(),
            "created_at": utcnow_iso(),
        })
        response.set_cookie(
            key="session_token",
            value=session_token,
            path="/",
            httponly=True,
            secure=True,
            samesite="none",
            max_age=SESSION_TTL_DAYS * 24 * 60 * 60,
        )
        return {"ok": True, "user": user.model_dump()}

    @router.get("/me")
    async def me(
        session_token_cookie: Optional[str] = Cookie(default=None, alias="session_token"),
        authorization: Optional[str] = Header(default=None),
    ):
        token = session_token_cookie
        if not token and authorization and authorization.lower().startswith("bearer "):
            token = authorization.split(None, 1)[1].strip()
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user = await _current_user_from_token(token)
        if not user:
            raise HTTPException(status_code=401, detail="Session expired")
        return user.model_dump()

    @router.post("/logout")
    async def logout(
        response: Response,
        session_token_cookie: Optional[str] = Cookie(default=None, alias="session_token"),
    ):
        if session_token_cookie:
            await db.user_sessions.delete_one({"session_token": session_token_cookie})
        response.delete_cookie("session_token", path="/")
        return {"ok": True}

    # Dev helper — get a bearer token for a demo user without going through Google.
    # SELF-HEALING: for the known demo allowlist, auto-create the user on first call
    # so fresh production deployments Just Work even if the seed hasn't run yet.
    DEMO_ALLOWLIST = {
        "demo.recruiter@levelshift.ai":  ("Ava Recruiter",   Role.RECRUITER.value),
        "demo.manager@levelshift.ai":    ("Marcus Manager",  Role.HIRING_MANAGER.value),
        "demo.executive@levelshift.ai":  ("Elena Executive", Role.EXECUTIVE.value),
    }
    DEMO_PICTURE = (
        "https://images.unsplash.com/photo-1500648767791-00dcc994a43e"
        "?crop=entropy&cs=srgb&fm=jpg&w=200"
    )

    @router.post("/dev-login")
    async def dev_login(email: str, response: Response):
        """Mint a session for a demo user. Auto-provisions from the allowlist."""
        import logging
        log = logging.getLogger("earos.auth")
        user_doc = await db.users.find_one({"email": email}, {"_id": 0})
        if not user_doc:
            if email not in DEMO_ALLOWLIST:
                log.warning("dev-login rejected — not in allowlist: %s", email)
                raise HTTPException(
                    status_code=404,
                    detail=f"Demo user not provisioned for {email}",
                )
            name, role = DEMO_ALLOWLIST[email]
            user_doc = {
                "user_id": new_user_id(),
                "email": email,
                "name": name,
                "picture": DEMO_PICTURE,
                "role": role,
                "organization_id": "org_levelshift",
                "created_at": utcnow_iso(),
            }
            await db.users.insert_one(user_doc)
            log.info("dev-login auto-provisioned demo user: %s (%s)", email, role)
            user_doc.pop("_id", None)

        session_token = f"dev_{os.urandom(24).hex()}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
        await db.user_sessions.insert_one({
            "user_id": user_doc["user_id"],
            "session_token": session_token,
            "expires_at": expires_at.isoformat(),
            "created_at": utcnow_iso(),
        })
        response.set_cookie(
            key="session_token",
            value=session_token,
            path="/",
            httponly=True,
            secure=True,
            samesite="none",
            max_age=SESSION_TTL_DAYS * 24 * 60 * 60,
        )
        return {"ok": True, "user": user_doc, "session_token": session_token}

    return router


async def get_current_user(
    request: Request, db: AsyncIOMotorDatabase
) -> AppUser:
    token = request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth.split(None, 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    expires_at = session["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    return AppUser(**user_doc)
