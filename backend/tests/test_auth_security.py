import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from applications.auth import (
    AppUser,
    _configured_session_data_url,
    _create_session,
    _provision_or_update_user,
    _read_session_user,
    validate_production_auth_configuration,
)


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


def test_production_rejects_a_missing_or_demonstration_identity_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EAROS_ENV", "production")
    monkeypatch.delenv("AUTH_SESSION_DATA_URL", raising=False)
    with pytest.raises(RuntimeError, match="explicitly configured"):
        _configured_session_data_url()

    monkeypatch.setenv("AUTH_SESSION_DATA_URL", "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data")
    with pytest.raises(RuntimeError, match="demonstration identity service"):
        _configured_session_data_url()


def test_production_auth_configuration_requires_safe_identity_url_and_no_dev_login(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EAROS_ENV", "production")
    monkeypatch.setenv("AUTH_SESSION_DATA_URL", "https://identity.example.com/session-data")
    monkeypatch.setenv("EAROS_ENABLE_DEV_LOGIN", "false")
    validate_production_auth_configuration()

    monkeypatch.setenv("EAROS_ENABLE_DEV_LOGIN", "true")
    with pytest.raises(RuntimeError, match="must be disabled"):
        validate_production_auth_configuration()


def test_jit_provisioning_ignores_upstream_elevated_role_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EAROS_ALLOW_JIT_PROVISIONING", "true")
    user = run(_provision_or_update_user(FakeDatabase(), {
        "email": "new-admin-claim@example.com",
        "name": "New user",
        "organization_id": "org_1",
        "role": "admin",
    }))
    assert user.role == "recruiter"
