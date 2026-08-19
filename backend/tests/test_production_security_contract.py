"""Fast contract checks for production security controls.

These tests deliberately inspect source contracts without connecting to MongoDB,
an upstream identity service, or any external integration.
"""
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
AUTH_SOURCE = (BACKEND / "applications" / "auth.py").read_text(encoding="utf-8")
SERVER_SOURCE = (BACKEND / "server.py").read_text(encoding="utf-8")


def test_sessions_are_persisted_as_hashes_not_raw_tokens() -> None:
    assert "session_token_hash" in AUTH_SOURCE
    assert "sha256(token.encode" in AUTH_SOURCE
    assert '"session_token": token' not in AUTH_SOURCE


def test_identity_provisioning_requires_explicit_tenant_assignment() -> None:
    assert "EAROS_ALLOW_JIT_PROVISIONING" in AUTH_SOURCE
    assert "Authenticated identity is missing an organization assignment" in AUTH_SOURCE
    assert "email.split" not in AUTH_SOURCE


def test_developer_login_is_disabled_unless_explicitly_enabled() -> None:
    assert "EAROS_ENABLE_DEV_LOGIN" in AUTH_SOURCE
    assert 'raise HTTPException(status_code=404, detail="Not found")' in AUTH_SOURCE


def test_production_cors_rejects_wildcard_configuration() -> None:
    assert "CORS_ORIGINS must be an explicit allowlist in production" in SERVER_SOURCE
    assert "allow_origins=_configured_cors_origins()" in SERVER_SOURCE
    assert 'allow_origins=os.environ.get("CORS_ORIGINS", "*")' not in SERVER_SOURCE


def test_bootstrap_requires_explicit_enablement_and_a_secret() -> None:
    assert "EAROS_ENABLE_BOOTSTRAP_ENDPOINT" in SERVER_SOURCE
    assert "EAROS_BOOTSTRAP_SECRET" in SERVER_SOURCE
    assert "Bootstrap authorization failed" in SERVER_SOURCE


def test_direct_resource_routes_use_tenant_scoped_helpers() -> None:
    assert "async def _scoped_job" in SERVER_SOURCE
    assert "async def _scoped_candidate" in SERVER_SOURCE
    assert "await _scoped_candidate(candidate_id, user)" in SERVER_SOURCE
    assert "await _scoped_job(job_id, user)" in SERVER_SOURCE


def test_policy_changes_are_reserved_for_administrators() -> None:
    policy_start = SERVER_SOURCE.index('async def upsert_policy')
    policy_block = SERVER_SOURCE[policy_start: policy_start + 450]
    assert "_require_role(user, Role.ADMIN)" in policy_block


def test_readiness_and_request_correlation_are_present() -> None:
    assert '@app.get("/api/ready", include_in_schema=False)' in SERVER_SOURCE
    assert 'await db.command("ping")' in SERVER_SOURCE
    assert 'response.headers["X-Request-ID"] = request_id' in SERVER_SOURCE


def test_policy_simulation_uses_the_authenticated_callers_role() -> None:
    simulation_start = SERVER_SOURCE.index("async def simulate_policy")
    simulation_block = SERVER_SOURCE[simulation_start: simulation_start + 700]
    assert "user_role=user.role" in simulation_block
    assert "user_role=req.user_role" not in simulation_block


def test_llm_backed_request_payloads_are_bounded() -> None:
    assert "goal: str = Field(min_length=3, max_length=2000)" in SERVER_SOURCE
    assert "steps: list[dict[str, Any]] = Field(min_length=1, max_length=20)" in SERVER_SOURCE
    assert "brief: str = Field(min_length=20, max_length=20_000)" in SERVER_SOURCE
    assert "resume_text: str = Field(min_length=20, max_length=200_000)" in SERVER_SOURCE


def test_policy_records_are_scoped_to_the_callers_organization() -> None:
    policy_source = (BACKEND / "platform_core" / "policy.py").read_text()
    live_activity_source = (BACKEND / "platform_core" / "live_activity.py").read_text()
    assert 'organization_id: str' in policy_source
    assert 'find({"organization_id": organization_id}' in policy_source
    assert 'self.list_policies(ctx.organization_id)' in policy_source
    assert '"policy_id": p.policy_id, "organization_id": p.organization_id' in policy_source
    assert '"organization_id": organization_id, "enabled": True' in live_activity_source


def test_policy_api_prevents_cross_tenant_read_and_delete() -> None:
    assert "policy_engine.list_policies(user.organization_id)" in SERVER_SOURCE
    assert 'Policy(organization_id=user.organization_id' in SERVER_SOURCE
    assert '"policy_id": policy_id, "organization_id": user.organization_id' in SERVER_SOURCE
