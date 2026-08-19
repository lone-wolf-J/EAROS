import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from applications.auth import AppUser, _create_session, _provision_or_update_user, _read_session_user


class FakeCollection:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    async def find_one(self, query: dict, _projection: dict | None = None):
        for row in self.rows:
            if all(row.get(key) == value for key, value in query.items()):
                return dict(row)
        return None

    async def insert_one(self, row: dict):
        self.rows.append(dict(row))

    async def update_one(self, query: dict, update: dict):
        row = await self.find_one(query)
        if row:
            row.update(update.get("$set", {}))
            for index, existing in enumerate(self.rows):
                if all(existing.get(key) == value for key, value in query.items()):
                    self.rows[index] = row
                    break


class FakeDatabase:
    def __init__(self) -> None:
        self.users = FakeCollection()
        self.user_sessions = FakeCollection()
        self.audit_events = FakeCollection()


class FakeRequest:
    headers = {"user-agent": "EAROS security test"}


def run(coroutine):
    return asyncio.run(coroutine)


def test_created_session_persists_only_a_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EAROS_SESSION_TTL_DAYS", "2")
    db = FakeDatabase()
    user = AppUser(user_id="user_1", email="recruiter@example.com", name="Recruiter", role="recruiter", organization_id="org_1")
    token = run(_create_session(db, user, FakeRequest()))
    assert token
    assert db.user_sessions.rows[0]["session_token_hash"] != token
    assert "session_token" not in db.user_sessions.rows[0]


def test_valid_session_resolves_the_user_from_the_digest() -> None:
    db = FakeDatabase()
    db.users.rows.append(AppUser(user_id="user_1", email="recruiter@example.com", name="Recruiter", role="recruiter", organization_id="org_1").model_dump())
    token = run(_create_session(db, AppUser(**db.users.rows[0]), FakeRequest()))
    user = run(_read_session_user(db, token))
    assert user is not None
    assert user.organization_id == "org_1"


def test_expired_session_cannot_resolve_a_user() -> None:
    db = FakeDatabase()
    db.users.rows.append(AppUser(user_id="user_1", email="recruiter@example.com", name="Recruiter", role="recruiter", organization_id="org_1").model_dump())
    db.user_sessions.rows.append({"user_id": "user_1", "session_token_hash": "not-a-match", "expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()})
    assert run(_read_session_user(db, "expired-token")) is None


def test_existing_identity_preserves_explicit_role_and_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EAROS_ALLOW_JIT_PROVISIONING", "false")
    db = FakeDatabase()
    db.users.rows.append(AppUser(user_id="user_1", email="admin@example.com", name="Admin", role="admin", organization_id="org_explicit").model_dump())
    user = run(_provision_or_update_user(db, {"email": "admin@example.com", "name": "Updated Name", "organization_id": "org_untrusted", "role": "candidate"}))
    assert user.role == "admin"
    assert user.organization_id == "org_explicit"


def test_new_identity_is_rejected_when_jit_provisioning_is_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EAROS_ALLOW_JIT_PROVISIONING", "false")
    with pytest.raises(HTTPException) as exc:
        run(_provision_or_update_user(FakeDatabase(), {"email": "new@example.com", "name": "New User", "organization_id": "org_1"}))
    assert exc.value.status_code == 403


def test_jit_provisioning_requires_an_explicit_organization(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EAROS_ALLOW_JIT_PROVISIONING", "true")
    monkeypatch.delenv("EAROS_DEFAULT_ORGANIZATION_ID", raising=False)
    with pytest.raises(HTTPException) as exc:
        run(_provision_or_update_user(FakeDatabase(), {"email": "new@example.com", "name": "New User"}))
    assert exc.value.status_code == 422
