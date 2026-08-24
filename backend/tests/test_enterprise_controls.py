"""Contract tests for EAROS enterprise compliance controls."""
import asyncio
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "earos_contract_tests")

import server
from foundation import ApplicationStatus, AuditExportStatus, DataSubjectRequestStatus, ExecutionStatus, RetentionCaseStatus, Role
from platform_core.capabilities import build_default_registry
from platform_core.governance import Governance
from platform_core.policy import PolicyEngine
from platform_core.runtime import Runtime
from platform_core.world import AuditExportManifest, Candidate, DataSubjectRequest, Requisition, RetentionCase
from test_governed_ats_capabilities import MemoryDB


def test_retention_case_is_review_only_and_scoped_to_a_tenant():
    case = RetentionCase(
        organization_id="org_alpha",
        subject_type="candidate",
        subject_id="cand_123",
        requested_action="erase",
        reason="Candidate submitted a verified data-erasure request.",
        requested_by_user_id="user_admin",
    )

    assert case.organization_id == "org_alpha"
    assert case.status is RetentionCaseStatus.PENDING_REVIEW
    assert case.legal_hold is False
    assert case.retention_case_id.startswith("ret_")


def test_audit_export_manifest_tracks_metadata_not_exported_bytes():
    manifest = AuditExportManifest(
        organization_id="org_alpha",
        requested_by_user_id="user_admin",
        filters={"event_type": "runtime.execution.completed"},
        event_count=12,
    )

    assert manifest.status is AuditExportStatus.REQUESTED
    assert manifest.storage_key is None
    assert manifest.audit_export_id.startswith("auditexp_")


def test_enterprise_control_routes_require_administrator_review_and_delegate_retention_execution_to_runtime():
    source = Path(__file__).parents[1].joinpath("server.py").read_text()

    assert '@app.post("/api/enterprise/retention-cases")' in source
    assert '@app.post("/api/enterprise/retention-cases/{retention_case_id}/execute")' in source
    assert '@app.post("/api/enterprise/audit-exports")' in source
    assert '"destructive_action_executed": False' in source
    assert '"execution": "approved cases execute only through the policy-evaluated runtime"' in source
    assert "RETENTION_EXECUTION_CAPABILITIES" in source
    assert "return await execute_plan(ExecuteRequest(" in source
    assert "_require_role(user, Role.ADMIN)" in source


def test_operational_summary_counts_only_records_loaded_for_the_current_tenant():
    source = Path(__file__).parents[1].joinpath("server.py").read_text()

    assert '@app.get("/api/enterprise/operational-summary")' in source
    for scoped_query in (
        "world.list_requisitions(user.organization_id, include_archived=True)",
        "world.list_candidates(user.organization_id)",
        "world.list_applications(user.organization_id, include_archived=True)",
        "world.list_interviews(user.organization_id)",
        "world.list_offers(user.organization_id)",
        "governance.list_approvals(user.organization_id)",
        "runtime.list_executions(user.organization_id)",
    ):
        assert scoped_query in source


def test_administration_readiness_is_admin_only_and_sso_is_metadata_only():
    source = Path(__file__).parents[1].joinpath("server.py").read_text()

    readiness_start = source.index('@app.get("/api/enterprise/administration/readiness")')
    readiness_body = source[readiness_start:source.index("# ============================================================\n#   REFLECTION", readiness_start)]
    assert "_require_role(user, Role.ADMIN)" in readiness_body
    assert '"status": "not_configured"' in readiness_body
    assert '"identity_provider_metadata_url"' in readiness_body
    assert '"x509_certificate"' in readiness_body
    assert "EAROS does not persist them in tenant records." in readiness_body
    assert "create_sso" not in readiness_body
    assert "insert_one" not in readiness_body
    assert '"integration_administration"' in readiness_body
    assert '"external_action_posture": "draft_only_until_administrator_configuration_and_human_approval"' in readiness_body
    assert "integration_job_distribution_adapters()" in readiness_body


def test_operational_summary_handler_returns_metrics_from_one_tenant_only(monkeypatch):
    calls = []

    class _World:
        async def list_requisitions(self, organization_id, include_archived):
            calls.append(("requisitions", organization_id, include_archived))
            return [SimpleNamespace(approval_status=SimpleNamespace(value="open")), SimpleNamespace(approval_status=SimpleNamespace(value="closed"))]

        async def list_candidates(self, organization_id):
            calls.append(("candidates", organization_id))
            return [object(), object(), object()]

        async def list_applications(self, organization_id, include_archived):
            calls.append(("applications", organization_id, include_archived))
            return [SimpleNamespace(status=SimpleNamespace(value="hired")), SimpleNamespace(status=SimpleNamespace(value="active"))]

        async def list_interviews(self, organization_id):
            calls.append(("interviews", organization_id))
            return [SimpleNamespace(status=SimpleNamespace(value="scheduled")), SimpleNamespace(status=SimpleNamespace(value="completed"))]

        async def list_offers(self, organization_id):
            calls.append(("offers", organization_id))
            return [SimpleNamespace(status=SimpleNamespace(value="accepted"))]

    class _Governance:
        async def list_approvals(self, organization_id):
            calls.append(("approvals", organization_id))
            return [SimpleNamespace(status="pending"), SimpleNamespace(status="granted")]

    class _Runtime:
        async def list_executions(self, organization_id):
            calls.append(("executions", organization_id))
            return [object(), object()]

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())
    monkeypatch.setattr(server, "runtime", _Runtime())

    result = asyncio.run(server.enterprise_operational_summary(SimpleNamespace(organization_id="org_alpha")))

    assert result == {
        "requisitions": {"total": 2, "open": 1},
        "candidates": {"total": 3},
        "applications": {"total": 2, "hired": 1},
        "interviews": {"total": 2, "scheduled": 1},
        "offers": {"total": 1, "accepted": 1},
        "governance": {"pending_approvals": 1, "executions": 2},
    }
    assert all(call[1] == "org_alpha" for call in calls)


def test_administration_readiness_handler_withholds_role_data_from_non_admins():
    admin_result = asyncio.run(server.enterprise_administration_readiness(SimpleNamespace(role=Role.ADMIN, organization_id="org_alpha")))

    assert {role["id"] for role in admin_result["roles"]} == {role.value for role in Role}
    assert admin_result["sso_saml"]["status"] == "not_configured"
    assert "secrets" not in admin_result["sso_saml"]
    assert admin_result["integration_administration"]["organization_id"] == "org_alpha"
    assert admin_result["integration_administration"]["status"] == "not_configured"
    assert admin_result["integration_administration"]["job_distribution_adapters"]
    assert all(adapter["configuration_state"] == "not_configured" for adapter in admin_result["integration_administration"]["job_distribution_adapters"])

    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.enterprise_administration_readiness(SimpleNamespace(role=Role.RECRUITER, organization_id="org_alpha")))
    assert exc.value.status_code == 403


def test_granted_retention_approval_decision_resumes_the_tenant_scoped_runtime(monkeypatch):
    calls = []
    approval = SimpleNamespace(
        approval_id="apr_retention",
        context={
            "capability_id": "cap.execute_retention_erasure",
            "execution_id": "exec_retention",
        },
        status="pending",
    )
    approval.model_dump = lambda: {
        "approval_id": approval.approval_id,
        "status": approval.status,
        "context": approval.context,
    }

    class _Governance:
        async def list_approvals(self, organization_id):
            calls.append(("list", organization_id))
            return [approval]

        async def decide_approval(self, approval_id, decision, decided_by, note):
            calls.append(("decide", approval_id, decision, decided_by, note))
            approval.status = decision
            return approval

        async def emit(self, event):
            calls.append(("event", event.event_type, event.organization_id))
            return event

    class _Runtime:
        async def resume_after_approval(self, execution_id, organization_id):
            calls.append(("resume", execution_id, organization_id))
            return SimpleNamespace(
                execution_id=execution_id,
                organization_id=organization_id,
                correlation_id="cor_resume_retention",
                status=ExecutionStatus.SUCCEEDED,
                step_results=[{
                    "capability_id": "cap.execute_retention_erasure",
                    "ok": True,
                    "output": {"retention_case_id": "ret_123", "subject_id": "cand_123", "action": "erase"},
                }],
                model_dump=lambda: {"execution_id": execution_id, "status": "succeeded"},
            )

    monkeypatch.setattr(server, "governance", _Governance())
    monkeypatch.setattr(server, "runtime", _Runtime())
    user = SimpleNamespace(user_id="usr_admin", organization_id="org_alpha", role=Role.ADMIN)
    request = server.DecideApprovalRequest(decision="granted", note="Retention request verified")

    result = asyncio.run(server.decide_approval("apr_retention", request, user))

    assert result["resumed_execution"] == {"execution_id": "exec_retention", "status": "succeeded"}
    assert ("resume", "exec_retention", "org_alpha") in calls
    assert any(call[0] == "event" for call in calls)


def test_retention_approval_decision_rejects_non_administrator(monkeypatch):
    approval = SimpleNamespace(
        approval_id="apr_retention",
        context={"capability_id": "cap.execute_retention_archive", "execution_id": "exec_retention"},
        status="pending",
    )

    class _Governance:
        async def list_approvals(self, _organization_id):
            return [approval]

    monkeypatch.setattr(server, "governance", _Governance())
    user = SimpleNamespace(user_id="usr_manager", organization_id="org_alpha", role=Role.HIRING_MANAGER)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.decide_approval(
            "apr_retention", server.DecideApprovalRequest(decision="granted"), user
        ))
    assert exc.value.status_code == 403


def test_hiring_decision_request_creates_tenant_scoped_approval_and_preserves_active_application(monkeypatch):
    calls = []
    application = SimpleNamespace(
        application_id="app_alpha",
        candidate_id="cand_alpha",
        requisition_id="req_alpha",
        status=ApplicationStatus.ACTIVE,
    )

    class _World:
        async def get_application(self, organization_id, application_id):
            calls.append(("application", organization_id, application_id))
            return application if (organization_id, application_id) == ("org_alpha", "app_alpha") else None

        async def list_hiring_decisions(self, organization_id, application_id=None, candidate_id=None):
            calls.append(("decisions", organization_id, application_id, candidate_id))
            return []

        async def create_hiring_decision(self, decision):
            calls.append(("create", decision.organization_id, decision.application_id, decision.status))
            return decision

        async def record_activity(self, activity):
            calls.append(("activity", activity.organization_id, activity.entity_id, activity.event_type))
            return activity

    class _Governance:
        async def request_approval(self, approval):
            calls.append(("approval", approval.organization_id, approval.subject_type, approval.subject_id))
            return approval

        async def emit(self, event):
            calls.append(("event", event.organization_id, event.event_type.value))
            return event

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())
    user = SimpleNamespace(user_id="usr_recruiter", organization_id="org_alpha", role=Role.RECRUITER)

    result = asyncio.run(server.request_ats_hiring_decision(
        server.HiringDecisionCreateRequest(
            application_id="app_alpha", outcome="hire", rationale="Panel evidence supports a final hiring decision after structured review."
        ),
        user,
    ))

    assert result["status"] == "awaiting_approval"
    assert result["approval"]["organization_id"] == "org_alpha"
    assert result["approval"]["subject_type"] == "hiring_decision"
    assert ("create", "org_alpha", "app_alpha", "awaiting_approval") in calls
    assert ("activity", "org_alpha", "cand_alpha", "hiring_decision.requested") in calls
    assert application.status is ApplicationStatus.ACTIVE


def test_hiring_decision_grant_requires_independent_approver_and_only_then_updates_application(monkeypatch):
    calls = []
    decision = SimpleNamespace(
        hiring_decision_id="hiredec_alpha",
        approval_id="apr_hiredec",
        application_id="app_alpha",
        candidate_id="cand_alpha",
        outcome="hire",
        status="awaiting_approval",
        model_dump=lambda: {"hiring_decision_id": "hiredec_alpha", "status": decision.status},
    )
    approval = SimpleNamespace(
        approval_id="apr_hiredec",
        subject_type="hiring_decision",
        subject_id="hiredec_alpha",
        requested_by="usr_recruiter",
        context={"hiring_decision_id": "hiredec_alpha"},
        status="pending",
        model_dump=lambda: {"approval_id": "apr_hiredec", "status": approval.status},
    )

    class _World:
        async def get_application(self, organization_id, application_id):
            calls.append(("application", organization_id, application_id))
            return SimpleNamespace(status=ApplicationStatus.ACTIVE) if (organization_id, application_id) == ("org_alpha", "app_alpha") else None

        async def get_hiring_decision(self, organization_id, hiring_decision_id):
            calls.append(("get", organization_id, hiring_decision_id))
            return decision if (organization_id, hiring_decision_id) == ("org_alpha", "hiredec_alpha") else None

        async def resolve_hiring_decision(self, organization_id, hiring_decision_id, **kwargs):
            calls.append(("resolve", organization_id, hiring_decision_id, kwargs["status"], kwargs["resolved_by_user_id"]))
            decision.status = kwargs["status"]
            return decision

        async def apply_hiring_decision_application_status(self, organization_id, resolved):
            calls.append(("apply", organization_id, resolved.application_id, resolved.outcome))
            return SimpleNamespace(status=ApplicationStatus.HIRED)

        async def record_activity(self, activity):
            calls.append(("activity", activity.organization_id, activity.entity_id, activity.event_type))
            return activity

    class _Governance:
        async def list_approvals(self, organization_id):
            calls.append(("list", organization_id))
            return [approval]

        async def decide_approval(self, approval_id, outcome, decided_by, note):
            calls.append(("decide", approval_id, outcome, decided_by))
            approval.status = outcome
            return approval

        async def emit(self, event):
            calls.append(("event", event.organization_id, event.event_type.value))
            return event

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())
    independent_admin = SimpleNamespace(user_id="usr_admin", organization_id="org_alpha", role=Role.ADMIN)
    requester = SimpleNamespace(user_id="usr_recruiter", organization_id="org_alpha", role=Role.RECRUITER)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.decide_approval(
            "apr_hiredec", server.DecideApprovalRequest(decision="denied"), requester
        ))
    assert exc.value.status_code == 403

    result = asyncio.run(server.decide_approval(
        "apr_hiredec", server.DecideApprovalRequest(decision="granted", note="Independent panel approval."), independent_admin
    ))

    assert result["hiring_decision"] == {"hiring_decision_id": "hiredec_alpha", "status": "effective"}
    assert ("apply", "org_alpha", "app_alpha", "hire") in calls
    assert ("activity", "org_alpha", "cand_alpha", "hiring_decision.effective") in calls

    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.decide_approval(
            "apr_hiredec", server.DecideApprovalRequest(decision="denied"), independent_admin
        ))
    assert exc.value.status_code == 409
    assert len([call for call in calls if call[0] == "activity"]) == 1


def test_hiring_decision_grant_rejects_a_stale_application_without_deciding_or_emitting_effects(monkeypatch):
    calls = []
    decision = SimpleNamespace(
        hiring_decision_id="hiredec_stale",
        approval_id="apr_hiredec_stale",
        application_id="app_stale",
    )
    approval = SimpleNamespace(
        approval_id="apr_hiredec_stale",
        subject_type="hiring_decision",
        subject_id="hiredec_stale",
        requested_by="usr_recruiter",
        context={"hiring_decision_id": "hiredec_stale"},
        status="pending",
    )

    class _World:
        async def get_hiring_decision(self, organization_id, hiring_decision_id):
            calls.append(("decision", organization_id, hiring_decision_id))
            return decision

        async def get_application(self, organization_id, application_id):
            calls.append(("application", organization_id, application_id))
            return SimpleNamespace(status=ApplicationStatus.REJECTED)

    class _Governance:
        async def list_approvals(self, organization_id):
            calls.append(("list", organization_id))
            return [approval]

        async def decide_approval(self, *_args):
            calls.append(("decide",))
            return approval

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())
    user = SimpleNamespace(user_id="usr_admin", organization_id="org_alpha", role=Role.ADMIN)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.decide_approval(
            "apr_hiredec_stale", server.DecideApprovalRequest(decision="granted"), user
        ))
    assert exc.value.status_code == 409
    assert not any(call[0] == "decide" for call in calls)


@pytest.mark.parametrize(
    ("requested_action", "status", "expected_capability"),
    [
        ("archive", RetentionCaseStatus.APPROVED_FOR_ARCHIVE, "cap.execute_retention_archive"),
        ("erase", RetentionCaseStatus.APPROVED_FOR_ERASURE, "cap.execute_retention_erasure"),
    ],
)
def test_retention_execution_api_dispatches_only_the_reviewed_governed_capability(
    monkeypatch, requested_action, status, expected_capability
):
    retention_case = RetentionCase(
        organization_id="org_alpha",
        subject_type="candidate",
        subject_id="cand_123",
        requested_action=requested_action,
        reason="Verified data retention request has completed administrator review.",
        requested_by_user_id="usr_admin",
        status=status,
    )
    captured = {}

    class _World:
        async def get_retention_case(self, organization_id, retention_case_id):
            return retention_case if (organization_id, retention_case_id) == ("org_alpha", retention_case.retention_case_id) else None

    async def _execute_plan(request, user):
        captured["request"] = request
        captured["user"] = user
        return {"status": "awaiting_approval"}

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "execute_plan", _execute_plan)
    user = SimpleNamespace(user_id="usr_admin", organization_id="org_alpha", role=Role.ADMIN)

    result = asyncio.run(server.execute_retention_case(retention_case.retention_case_id, user))

    assert result == {"status": "awaiting_approval"}
    assert captured["request"].steps[0]["capability_id"] == expected_capability
    assert captured["request"].steps[0]["inputs"] == {"retention_case_id": retention_case.retention_case_id}


def test_retention_execution_api_blocks_a_legal_hold_before_runtime_dispatch(monkeypatch):
    retention_case = RetentionCase(
        organization_id="org_alpha",
        subject_type="candidate",
        subject_id="cand_123",
        requested_action="erase",
        reason="Legal hold protects this reviewed subject from destructive retention action.",
        requested_by_user_id="usr_admin",
        status=RetentionCaseStatus.APPROVED_FOR_ERASURE,
        legal_hold=True,
    )

    class _World:
        async def get_retention_case(self, _organization_id, _retention_case_id):
            return retention_case

    async def _unexpected_execute(*_args, **_kwargs):
        raise AssertionError("legal-hold case must never reach the runtime")

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "execute_plan", _unexpected_execute)
    user = SimpleNamespace(user_id="usr_admin", organization_id="org_alpha", role=Role.ADMIN)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.execute_retention_case(retention_case.retention_case_id, user))
    assert exc.value.status_code == 409


class _EndpointLifecycleWorld:
    def __init__(self):
        self.candidate = Candidate(
            organization_id="org_alpha",
            full_name="Endpoint Candidate",
            email="endpoint@example.com",
            phone="555-0100",
            skills=["Python", "Kubernetes"],
            notes=[{"body": "Operational note"}],
        )
        self.cases = {}

    async def get_candidate_for_organization(self, organization_id, candidate_id):
        if organization_id == "org_alpha" and candidate_id == self.candidate.candidate_id:
            return self.candidate
        return None

    async def create_retention_case(self, retention_case):
        self.cases[retention_case.retention_case_id] = retention_case
        return retention_case

    async def decide_retention_case(self, organization_id, retention_case_id, *, status, reviewed_by_user_id, decision_note=None):
        retention_case = self.cases.get(retention_case_id)
        if not retention_case or organization_id != "org_alpha":
            return None
        retention_case.status = status
        retention_case.reviewed_by_user_id = reviewed_by_user_id
        retention_case.decision_note = decision_note
        return retention_case

    async def get_retention_case(self, organization_id, retention_case_id):
        retention_case = self.cases.get(retention_case_id)
        return retention_case if retention_case and organization_id == "org_alpha" else None

    async def execute_retention_case(self, organization_id, retention_case_id, *, expected_action):
        retention_case = await self.get_retention_case(organization_id, retention_case_id)
        if not retention_case or retention_case.legal_hold:
            return None
        if expected_action == "archive":
            self.candidate.archived_at = "2026-08-19T00:00:00+00:00"
        else:
            self.candidate.full_name = "Redacted candidate"
            self.candidate.email = None
            self.candidate.phone = None
            self.candidate.skills = []
            self.candidate.notes = []
            self.candidate.erased_at = "2026-08-19T00:00:00+00:00"
        retention_case.status = RetentionCaseStatus.COMPLETED
        return retention_case

    async def list_candidates(self, organization_id):
        if organization_id != "org_alpha" or self.candidate.archived_at:
            return []
        return [self.candidate]


@pytest.mark.parametrize(
    ("requested_action", "review_status"),
    [
        ("archive", RetentionCaseStatus.APPROVED_FOR_ARCHIVE),
        ("erase", RetentionCaseStatus.APPROVED_FOR_ERASURE),
    ],
)
def test_retention_endpoints_complete_review_approval_resume_and_subject_state(monkeypatch, requested_action, review_status):
    world = _EndpointLifecycleWorld()
    db = MemoryDB()
    governance = Governance(db)
    policy = PolicyEngine(db, governance)
    runtime = Runtime(db, world, build_default_registry(), policy, governance)
    monkeypatch.setattr(server, "world", world)
    monkeypatch.setattr(server, "governance", governance)
    monkeypatch.setattr(server, "runtime", runtime)
    user = SimpleNamespace(user_id="usr_admin", organization_id="org_alpha", role=Role.ADMIN)

    async def run_lifecycle():
        created = await server.create_retention_case(
            server.CreateRetentionCaseRequest(
                subject_type="candidate", subject_id=world.candidate.candidate_id,
                requested_action=requested_action,
                reason="Endpoint-level retention request requires review, approval, and immutable audit evidence.",
            ), user,
        )
        reviewed = await server.decide_retention_case(
            created["retention_case_id"],
            server.DecideRetentionCaseRequest(decision=review_status.value, note="Administrator review completed."),
            user,
        )
        queued = await server.execute_retention_case(reviewed["retention_case_id"], user)
        assert queued["status"] == ExecutionStatus.AWAITING_APPROVAL.value
        assert world.candidate.archived_at is None
        assert world.candidate.erased_at is None
        approval = (await governance.list_approvals("org_alpha"))[0]
        approved = await server.decide_approval(
            approval.approval_id,
            server.DecideApprovalRequest(decision="granted", note="Execution approved."),
            user,
        )
        events = await governance.replay(queued["correlation_id"])
        return created, approved, events

    created, approved, events = asyncio.run(run_lifecycle())

    assert approved["resumed_execution"]["status"] == ExecutionStatus.SUCCEEDED.value
    assert world.cases[created["retention_case_id"]].status == RetentionCaseStatus.COMPLETED
    if requested_action == "archive":
        assert world.candidate.archived_at is not None
        assert asyncio.run(world.list_candidates("org_alpha")) == []
    else:
        assert world.candidate.erased_at is not None
        assert world.candidate.full_name == "Redacted candidate"
        assert world.candidate.email is None
        assert world.candidate.skills == []
    assert any(event.event_type.value.startswith("world.retention") for event in events)


def test_held_retention_endpoint_leaves_active_candidate_unchanged(monkeypatch):
    world = _EndpointLifecycleWorld()
    retention_case = RetentionCase(
        organization_id="org_alpha", subject_type="candidate", subject_id=world.candidate.candidate_id,
        requested_action="erase", reason="Legal hold preserves the candidate pending external matter resolution.",
        requested_by_user_id="usr_admin", status=RetentionCaseStatus.APPROVED_FOR_ERASURE, legal_hold=True,
    )
    world.cases[retention_case.retention_case_id] = retention_case
    monkeypatch.setattr(server, "world", world)
    user = SimpleNamespace(user_id="usr_admin", organization_id="org_alpha", role=Role.ADMIN)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.execute_retention_case(retention_case.retention_case_id, user))

    assert exc.value.status_code == 409
    assert asyncio.run(world.list_candidates("org_alpha")) == [world.candidate]
    assert world.candidate.erased_at is None
    assert world.candidate.full_name == "Endpoint Candidate"


def test_onboarding_handoff_handler_requires_an_accepted_matching_offer_and_emits_audit_records(monkeypatch):
    calls = []

    class _World:
        async def get_offer(self, organization_id, offer_id):
            calls.append(("offer", organization_id, offer_id))
            return SimpleNamespace(
                candidate_id="cand_alpha",
                job_id="job_alpha",
                status=SimpleNamespace(value="accepted"),
            )

        async def upsert_onboarding_handoff(self, handoff):
            calls.append(("handoff", handoff.organization_id, handoff.offer_id))
            return handoff

        async def record_activity(self, activity):
            calls.append(("activity", activity.organization_id, activity.event_type))
            return activity

    class _Governance:
        async def emit(self, event):
            calls.append(("event", event.organization_id, event.event_type.value))

    async def _candidate(candidate_id, user):
        calls.append(("candidate", user.organization_id, candidate_id))
        return SimpleNamespace(candidate_id=candidate_id)

    async def _job(job_id, user):
        calls.append(("job", user.organization_id, job_id))
        return SimpleNamespace(job_id=job_id)

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())
    monkeypatch.setattr(server, "_scoped_candidate", _candidate)
    monkeypatch.setattr(server, "_scoped_job", _job)
    request = server.OnboardingHandoffCreateRequest(
        offer_id="offer_alpha",
        candidate_id="cand_alpha",
        job_id="job_alpha",
        destination_system="hris_connector",
    )
    user = SimpleNamespace(user_id="admin_alpha", organization_id="org_alpha", role=Role.ADMIN)

    result = asyncio.run(server.create_ats_onboarding_handoff(request, user))

    assert result["organization_id"] == "org_alpha"
    assert result["destination_system"] == "hris_connector"
    assert ("offer", "org_alpha", "offer_alpha") in calls
    assert ("activity", "org_alpha", "onboarding_handoff.created") in calls
    assert ("event", "org_alpha", "world.onboarding_handoff.created") in calls


def test_onboarding_handoff_handler_rejects_nonaccepted_offers(monkeypatch):
    class _World:
        async def get_offer(self, _organization_id, _offer_id):
            return SimpleNamespace(
                candidate_id="cand_alpha",
                job_id="job_alpha",
                status=SimpleNamespace(value="extended"),
            )

    async def _entity(*_args):
        return SimpleNamespace()

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "_scoped_candidate", _entity)
    monkeypatch.setattr(server, "_scoped_job", _entity)
    request = server.OnboardingHandoffCreateRequest(
        offer_id="offer_alpha", candidate_id="cand_alpha", job_id="job_alpha"
    )
    user = SimpleNamespace(user_id="admin_alpha", organization_id="org_alpha", role=Role.ADMIN)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.create_ats_onboarding_handoff(request, user))
    assert exc.value.status_code == 400
    assert "accepted offer" in exc.value.detail


def test_interview_feedback_handler_scopes_the_interview_and_records_candidate_activity(monkeypatch):
    calls = []

    class _World:
        async def get_interview(self, organization_id, interview_id):
            calls.append(("interview", organization_id, interview_id))
            return SimpleNamespace(candidate_id="cand_alpha")

        async def get_scorecard(self, organization_id, scorecard_id):
            calls.append(("scorecard", organization_id, scorecard_id))
            return SimpleNamespace(scorecard_id=scorecard_id)

        async def upsert_interview_feedback(self, feedback):
            calls.append(("feedback", feedback.organization_id, feedback.interviewer_id, feedback.recommendation))
            return feedback

        async def record_activity(self, activity):
            calls.append(("activity", activity.organization_id, activity.entity_type, activity.entity_id, activity.event_type))
            return activity

    class _Governance:
        async def emit(self, event):
            calls.append(("event", event.organization_id, event.event_type.value, event.subject_id))

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())
    user = SimpleNamespace(user_id="manager_alpha", organization_id="org_alpha", role=Role.HIRING_MANAGER)
    request = server.InterviewFeedbackCreateRequest(
        scorecard_id="scorecard_alpha",
        recommendation="yes",
        ratings={"Role evidence": 4},
        strengths=["Relevant operating experience"],
        summary="Evidence-based hiring-manager feedback.",
    )

    result = asyncio.run(server.create_ats_interview_feedback("interview_alpha", request, user))

    assert result["organization_id"] == "org_alpha"
    assert result["interviewer_id"] == "manager_alpha"
    assert ("interview", "org_alpha", "interview_alpha") in calls
    assert ("scorecard", "org_alpha", "scorecard_alpha") in calls
    assert ("feedback", "org_alpha", "manager_alpha", "yes") in calls
    assert ("activity", "org_alpha", "candidate", "cand_alpha", "interview.feedback_submitted") in calls
    assert ("event", "org_alpha", "world.scorecard.submitted", "interview_alpha") in calls


def test_publication_state_is_tenant_scoped_and_never_externalizes_a_requisition(monkeypatch):
    calls = []
    requisition = Requisition(organization_id="org_alpha", title="Platform Engineer")

    class _World:
        async def get_requisition(self, organization_id, requisition_id):
            calls.append(("get", organization_id, requisition_id))
            return requisition if requisition_id == requisition.requisition_id else None

        async def upsert_requisition(self, value):
            calls.append(("upsert", value.organization_id, value.external_publication_status, value.external_publication_targets))
            return value

        async def record_activity(self, activity):
            calls.append(("activity", activity.organization_id, activity.event_type))
            return activity

    class _Governance:
        async def emit(self, event):
            calls.append(("event", event.organization_id, event.event_type.value))

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())
    user = SimpleNamespace(user_id="recruiter_alpha", organization_id="org_alpha", role=Role.RECRUITER)
    request = server.RequisitionPublicationUpdateRequest(
        internal_publication_status="published",
        external_publication_status="pending_approval",
        external_publication_targets=["indeed", "linkedin"],
        career_site_enabled=True,
        referral_intake_enabled=True,
    )

    result = asyncio.run(server.update_ats_requisition_publication(requisition.requisition_id, request, user))

    assert result["internal_publication_status"] == "published"
    assert result["external_publication_status"] == "pending_approval"
    assert result["external_publication_targets"] == ["indeed", "linkedin"]
    assert ("upsert", "org_alpha", "pending_approval", ["indeed", "linkedin"]) in calls
    assert ("activity", "org_alpha", "requisition.publication_updated") in calls
    assert ("event", "org_alpha", "world.requisition.publication_updated") in calls


def test_notification_preferences_are_personal_tenant_scoped_records_with_inactive_provider_delivery(monkeypatch):
    calls = []

    class _World:
        async def get_notification_preference(self, organization_id, user_id):
            calls.append(("get", organization_id, user_id))
            return None

        async def upsert_notification_preference(self, preference):
            calls.append(("upsert", preference.organization_id, preference.user_id, preference.email_enabled, preference.provider_delivery_state))
            return preference

        async def record_activity(self, activity):
            calls.append(("activity", activity.organization_id, activity.entity_id, activity.event_type))
            return activity

    class _Governance:
        async def emit(self, event):
            calls.append(("event", event.organization_id, event.event_type.value))

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())
    user = SimpleNamespace(user_id="recruiter_alpha", organization_id="org_alpha", role=Role.RECRUITER)
    request = server.NotificationPreferenceUpdateRequest(email_enabled=True, approval_alerts=False)

    result = asyncio.run(server.update_ats_notification_preferences(request, user))

    assert result["organization_id"] == "org_alpha"
    assert result["user_id"] == "recruiter_alpha"
    assert result["provider_delivery_state"] == "not_configured"
    assert ("upsert", "org_alpha", "recruiter_alpha", True, "not_configured") in calls
    assert ("activity", "org_alpha", "recruiter_alpha", "notification.preferences_updated") in calls
    assert ("event", "org_alpha", "world.notification_preference.updated") in calls


def test_candidate_communication_requires_active_consent_for_outbound_email(monkeypatch):
    class _World:
        async def list_candidate_consents(self, *_args):
            return []

    async def _candidate(*_args):
        return SimpleNamespace(candidate_id="cand_alpha")

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "_scoped_candidate", _candidate)
    user = SimpleNamespace(user_id="recruiter_alpha", organization_id="org_alpha", role=Role.RECRUITER)
    request = server.CandidateCommunicationCreateRequest(direction="outbound", channel="email", subject="Interview update")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.record_ats_candidate_communication("cand_alpha", request, user))

    assert exc.value.status_code == 409
    assert "consent" in exc.value.detail.lower()


def test_candidate_communication_records_active_consent_and_candidate_activity(monkeypatch):
    calls = []

    class _World:
        async def list_candidate_consents(self, *_args):
            return [server.CandidateConsent(organization_id="org_alpha", candidate_id="cand_alpha", purpose="recruiting")]

        async def record_candidate_communication(self, communication):
            calls.append(("communication", communication.organization_id, communication.candidate_id, communication.consent_id))
            return communication

        async def record_activity(self, activity):
            calls.append(("activity", activity.organization_id, activity.entity_id, activity.event_type))
            return activity

    class _Governance:
        async def emit(self, event):
            calls.append(("event", event.organization_id, event.event_type.value, event.subject_id))

    async def _candidate(*_args):
        return SimpleNamespace(candidate_id="cand_alpha")

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())
    monkeypatch.setattr(server, "_scoped_candidate", _candidate)
    user = SimpleNamespace(user_id="recruiter_alpha", organization_id="org_alpha", role=Role.RECRUITER)
    request = server.CandidateCommunicationCreateRequest(direction="outbound", channel="email", subject="Interview update")

    result = asyncio.run(server.record_ats_candidate_communication("cand_alpha", request, user))

    assert result["organization_id"] == "org_alpha"
    assert result["delivery_state"] == "recorded"
    assert calls[0][0:3] == ("communication", "org_alpha", "cand_alpha")
    assert ("activity", "org_alpha", "cand_alpha", "candidate.communication_recorded") in calls
    assert ("event", "org_alpha", "world.candidate_communication.recorded", "cand_alpha") in calls


def test_collaboration_mention_validates_a_tenant_user_and_records_candidate_activity(monkeypatch):
    calls = []

    class _Users:
        async def find_one(self, query, _projection):
            calls.append(("user_lookup", query["user_id"], query["organization_id"]))
            return {"user_id": query["user_id"], "organization_id": query["organization_id"]}

    class _World:
        async def record_collaboration_mention(self, mention):
            calls.append(("mention", mention.organization_id, mention.candidate_id, mention.mentioned_user_id))
            return mention

        async def record_activity(self, activity):
            calls.append(("activity", activity.organization_id, activity.entity_id, activity.event_type))
            return activity

    class _Governance:
        async def emit(self, event):
            calls.append(("event", event.organization_id, event.event_type.value, event.subject_id))

    async def _candidate(*_args):
        return SimpleNamespace(candidate_id="cand_alpha")

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())
    monkeypatch.setattr(server, "db", SimpleNamespace(users=_Users()))
    monkeypatch.setattr(server, "_scoped_candidate", _candidate)
    user = SimpleNamespace(user_id="manager_alpha", organization_id="org_alpha", role=Role.HIRING_MANAGER)
    request = server.CollaborationMentionCreateRequest(
        mentioned_user_id="recruiter_alpha", context="Please review the structured feedback."
    )

    result = asyncio.run(server.create_ats_candidate_mention("cand_alpha", request, user))

    assert result["organization_id"] == "org_alpha"
    assert result["mentioned_user_id"] == "recruiter_alpha"
    assert ("user_lookup", "recruiter_alpha", "org_alpha") in calls
    assert ("mention", "org_alpha", "cand_alpha", "recruiter_alpha") in calls
    assert ("activity", "org_alpha", "cand_alpha", "collaboration.mention_created") in calls
    assert ("event", "org_alpha", "world.collaboration_mention.created", "cand_alpha") in calls


def test_candidate_notification_delivery_requires_consent_and_records_inactive_provider_state(monkeypatch):
    class _WorldWithoutConsent:
        async def list_candidate_consents(self, *_args):
            return []

    async def _candidate(*_args):
        return SimpleNamespace(candidate_id="cand_alpha")

    monkeypatch.setattr(server, "world", _WorldWithoutConsent())
    monkeypatch.setattr(server, "_scoped_candidate", _candidate)
    user = SimpleNamespace(user_id="recruiter_alpha", organization_id="org_alpha", role=Role.RECRUITER)
    request = server.CandidateNotificationDeliveryCreateRequest(notification_type="application_received", channel="email")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.record_ats_candidate_notification_delivery("cand_alpha", request, user))

    assert exc.value.status_code == 409
    assert "consent" in exc.value.detail.lower()


def test_candidate_notification_delivery_records_audit_and_never_claims_provider_delivery(monkeypatch):
    calls = []

    class _World:
        async def list_candidate_consents(self, *_args):
            return [server.CandidateConsent(organization_id="org_alpha", candidate_id="cand_alpha", purpose="recruiting")]

        async def record_candidate_notification_delivery(self, delivery):
            calls.append(("delivery", delivery.organization_id, delivery.candidate_id, delivery.delivery_state, delivery.consent_id))
            return delivery

        async def record_activity(self, activity):
            calls.append(("activity", activity.organization_id, activity.entity_id, activity.event_type, activity.payload["delivery_state"]))
            return activity

    class _Governance:
        async def emit(self, event):
            calls.append(("event", event.organization_id, event.event_type.value, event.payload["delivery_state"]))

    async def _candidate(*_args):
        return SimpleNamespace(candidate_id="cand_alpha")

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())
    monkeypatch.setattr(server, "_scoped_candidate", _candidate)
    user = SimpleNamespace(user_id="recruiter_alpha", organization_id="org_alpha", role=Role.RECRUITER)
    request = server.CandidateNotificationDeliveryCreateRequest(notification_type="interview_scheduled", channel="email")

    result = asyncio.run(server.record_ats_candidate_notification_delivery("cand_alpha", request, user))

    assert result["delivery_state"] == "not_delivered"
    assert ("delivery", "org_alpha", "cand_alpha", "not_delivered", result["consent_id"]) in calls
    assert ("activity", "org_alpha", "cand_alpha", "candidate.notification_recorded", "not_delivered") in calls
    assert ("event", "org_alpha", "world.candidate_notification.recorded", "not_delivered") in calls


def test_lifecycle_candidate_notification_is_consent_aware_and_never_claims_delivery(monkeypatch):
    calls = []

    class _World:
        async def list_candidate_consents(self, organization_id, candidate_id):
            assert (organization_id, candidate_id) == ("org_alpha", "cand_alpha")
            return [server.CandidateConsent(organization_id=organization_id, candidate_id=candidate_id, purpose="recruiting")]

        async def record_candidate_notification_delivery(self, delivery):
            calls.append(("delivery", delivery.notification_type, delivery.delivery_state, delivery.delivery_reason, delivery.consent_id))
            return delivery

        async def record_activity(self, activity):
            calls.append(("activity", activity.organization_id, activity.entity_id, activity.event_type))
            return activity

    class _Governance:
        async def emit(self, event):
            calls.append(("event", event.event_type.value, event.payload["delivery_state"]))

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())

    result = asyncio.run(server._record_lifecycle_candidate_notification(
        organization_id="org_alpha", candidate_id="cand_alpha", notification_type="offer_extended",
        subject="Offer decision approved", body="record-only", actor_user_id="admin_alpha",
    ))

    assert result and result.delivery_state == "not_delivered"
    assert ("delivery", "offer_extended", "not_delivered", "provider_not_configured", result.consent_id) in calls
    assert ("event", "world.candidate_notification.recorded", "not_delivered") in calls
    assert ("activity", "org_alpha", "cand_alpha", "candidate.lifecycle_notification_recorded") in calls


def test_lifecycle_recruiter_alerts_are_tenant_scoped_and_honor_in_app_preference(monkeypatch):
    calls = []

    class _Users:
        async def find_one(self, query, _projection):
            calls.append(("lookup", query["user_id"], query["organization_id"]))
            return {"user_id": query["user_id"], "organization_id": query["organization_id"]} if query["user_id"] != "foreign_user" else None

    class _World:
        async def get_notification_preference(self, _organization_id, user_id):
            return SimpleNamespace(in_app_enabled=user_id != "muted_user")

        async def create_recruiter_alert(self, alert):
            calls.append(("alert", alert.organization_id, alert.recipient_user_id, alert.alert_type, alert.status))
            return alert

    class _Governance:
        async def emit(self, event):
            calls.append(("event", event.event_type.value, event.payload["recipient_user_id"]))

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())
    monkeypatch.setattr(server, "db", SimpleNamespace(users=_Users()))

    alerts = asyncio.run(server._create_lifecycle_recruiter_alerts(
        organization_id="org_alpha", recipient_user_ids=["recruiter_alpha", "muted_user", "foreign_user", "recruiter_alpha"],
        alert_type="pipeline_stage_changed", title="Stage changed", body="record-only alert",
        entity_type="application", entity_id="app_alpha", actor_user_id="recruiter_alpha",
    ))

    assert [alert.recipient_user_id for alert in alerts] == ["recruiter_alpha"]
    assert ("alert", "org_alpha", "recruiter_alpha", "pipeline_stage_changed", "unread") in calls
    assert ("event", "world.recruiter_alert.created", "recruiter_alpha") in calls
    assert ("lookup", "foreign_user", "org_alpha") in calls


def test_recruiter_alert_validates_recipient_within_active_tenant(monkeypatch):
    calls = []

    class _Users:
        async def find_one(self, query, _projection):
            calls.append(("user_lookup", query["user_id"], query["organization_id"]))
            return {"user_id": query["user_id"], "organization_id": query["organization_id"]}

    class _World:
        async def create_recruiter_alert(self, alert):
            calls.append(("alert", alert.organization_id, alert.recipient_user_id, alert.alert_type))
            return alert

    class _Governance:
        async def emit(self, event):
            calls.append(("event", event.organization_id, event.event_type.value, event.payload["recipient_user_id"]))

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())
    monkeypatch.setattr(server, "db", SimpleNamespace(users=_Users()))
    user = SimpleNamespace(user_id="manager_alpha", organization_id="org_alpha", role=Role.HIRING_MANAGER)
    request = server.RecruiterAlertCreateRequest(
        recipient_user_id="recruiter_alpha", alert_type="interview_reminder", title="Interview review needed"
    )

    result = asyncio.run(server.create_ats_recruiter_alert(request, user))

    assert result["organization_id"] == "org_alpha"
    assert result["status"] == "unread"
    assert ("user_lookup", "recruiter_alpha", "org_alpha") in calls
    assert ("alert", "org_alpha", "recruiter_alpha", "interview_reminder") in calls
    assert ("event", "org_alpha", "world.recruiter_alert.created", "recruiter_alpha") in calls


def test_career_site_application_requires_consent_and_creates_canonical_records(monkeypatch):
    calls = []
    requisition = server.Requisition(
        organization_id="org_alpha",
        title="Platform Engineer",
        approval_status="open",
        internal_publication_status="published",
        career_site_enabled=True,
    )

    class _World:
        async def get_requisition(self, organization_id, requisition_id):
            calls.append(("requisition", organization_id, requisition_id))
            return requisition

        async def find_duplicate_candidate(self, *_args, **_kwargs):
            return None

        async def upsert_candidate(self, candidate):
            calls.append(("candidate", candidate.source, candidate.source_detail))
            return candidate

        async def upsert_consent(self, consent):
            calls.append(("consent", consent.purpose, consent.captured_from))
            return consent

        async def list_applications(self, *_args, **_kwargs):
            return []

        async def upsert_application(self, application):
            calls.append(("application", application.source, application.requisition_id))
            return application

        async def record_activity(self, activity):
            calls.append(("activity", activity.event_type, activity.entity_type))
            return activity

    class _Governance:
        async def emit(self, event):
            calls.append(("event", event.event_type.value, event.actor))

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())
    rejected = server.CareerSiteApplicationRequest(
        organization_id="org_alpha", full_name="Casey Candidate", email="casey@example.test"
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.submit_career_site_application(requisition.requisition_id, rejected))
    assert exc.value.status_code == 409

    accepted = server.CareerSiteApplicationRequest(
        organization_id="org_alpha", full_name="Casey Candidate", email="casey@example.test", consent_to_recruit=True
    )
    result = asyncio.run(server.submit_career_site_application(requisition.requisition_id, accepted))

    assert result["status"] == "received"
    assert ("candidate", "career_site", f"career_site:{requisition.requisition_id}") in calls
    assert ("consent", "recruiting", "career_site") in calls
    assert ("application", "career_site", requisition.requisition_id) in calls
    assert ("event", "world.career_site_application.received", "public:career_site") in calls


def test_career_site_withdrawal_requires_private_reference_and_preserves_application_provenance(monkeypatch):
    calls = []
    reference = "w" * 48
    application = server.Application(
        organization_id="org_alpha",
        candidate_id="cand_alpha",
        requisition_id="req_alpha",
        current_stage_name="Interview",
        stage_history=[{"stage_name": "Applied", "actor_user_id": "public:career_site"}],
        withdrawal_token_hash=server._withdrawal_reference_hash(reference),
    )

    class _World:
        async def get_application_by_id(self, application_id):
            calls.append(("lookup", application_id))
            return application if application_id == application.application_id else None

        async def upsert_application(self, updated):
            calls.append(("upsert", updated.organization_id, updated.status.value, updated.current_stage_name))
            return updated

        async def record_activity(self, activity):
            calls.append(("activity", activity.organization_id, activity.event_type))
            return activity

    class _Governance:
        async def emit(self, event):
            calls.append(("event", event.organization_id, event.event_type.value, event.actor))

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())
    request = server.CareerSiteApplicationWithdrawalRequest(
        withdrawal_reference=reference, reason="I accepted another opportunity."
    )

    result = asyncio.run(server.withdraw_career_site_application(application.application_id, request))

    assert result["status"] == "withdrawn"
    assert application.status is server.ApplicationStatus.WITHDRAWN
    assert application.current_stage_name == "Withdrawn"
    assert application.withdrawal_reason == "I accepted another opportunity."
    assert application.stage_history[-1]["actor_user_id"] == "public:candidate_withdrawal"
    assert ("upsert", "org_alpha", "withdrawn", "Withdrawn") in calls
    assert ("event", "org_alpha", "world.application.withdrawn", "public:candidate_withdrawal") in calls
    assert ("activity", "org_alpha", "application.withdrawn_by_candidate") in calls


def test_career_site_withdrawal_rejects_invalid_private_reference_without_mutation(monkeypatch):
    application = server.Application(
        organization_id="org_beta",
        candidate_id="cand_beta",
        withdrawal_token_hash=server._withdrawal_reference_hash("z" * 48),
    )

    class _World:
        async def get_application_by_id(self, _application_id):
            return application

        async def upsert_application(self, _updated):
            raise AssertionError("An invalid public reference must not persist an application change")

        async def record_activity(self, _activity):
            raise AssertionError("An invalid public reference must not create activity")

    class _Governance:
        async def emit(self, _event):
            raise AssertionError("An invalid public reference must not emit an event")

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())

    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.withdraw_career_site_application(
            application.application_id,
            server.CareerSiteApplicationWithdrawalRequest(withdrawal_reference="x" * 48),
        ))

    assert exc.value.status_code == 404
    assert application.status is server.ApplicationStatus.ACTIVE


def test_referral_intake_requires_enabled_requisition_and_validates_referrer(monkeypatch):
    calls = []
    requisition = server.Requisition(
        organization_id="org_alpha", title="Platform Engineer", approval_status="open", referral_intake_enabled=True
    )

    class _World:
        async def find_duplicate_candidate(self, *_args, **_kwargs):
            return None

        async def upsert_candidate(self, candidate):
            calls.append(("candidate", candidate.source, candidate.source_detail))
            return candidate

        async def list_applications(self, *_args, **_kwargs):
            return []

        async def upsert_application(self, application):
            calls.append(("application", application.source, application.referral_user_id))
            return application

        async def record_activity(self, activity):
            calls.append(("activity", activity.event_type, activity.payload["referrer_user_id"]))
            return activity

    class _Users:
        async def find_one(self, query, _projection):
            calls.append(("referrer_lookup", query["user_id"], query["organization_id"]))
            return {"user_id": query["user_id"], "organization_id": query["organization_id"]}

    class _Governance:
        async def emit(self, event):
            calls.append(("event", event.event_type.value, event.payload["referrer_user_id"]))

    async def _scoped_requisition(*_args):
        return requisition

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())
    monkeypatch.setattr(server, "db", SimpleNamespace(users=_Users()))
    monkeypatch.setattr(server, "_scoped_requisition", _scoped_requisition)
    user = SimpleNamespace(user_id="manager_alpha", organization_id="org_alpha", role=Role.HIRING_MANAGER)
    request = server.ReferralIntakeRequest(
        full_name="Taylor Referral", email="taylor@example.test", referrer_user_id="manager_alpha"
    )

    result = asyncio.run(server.record_ats_referral_intake(requisition.requisition_id, request, user))

    assert result["candidate_created"] is True
    assert ("referrer_lookup", "manager_alpha", "org_alpha") in calls
    assert ("candidate", "referral", "employee_referral:manager_alpha") in calls
    assert ("application", "referral", "manager_alpha") in calls
    assert ("event", "world.referral_intake.recorded", "manager_alpha") in calls


def test_data_subject_access_request_is_tenant_scoped_reviewed_and_linked_to_an_audit_manifest(monkeypatch):
    calls = []
    candidate = Candidate(
        organization_id="org_alpha", full_name="Casey Candidate", email="casey@example.test"
    )
    request = DataSubjectRequest(
        organization_id="org_alpha",
        candidate_id=candidate.candidate_id,
        request_type="access",
        request_summary="Candidate requested an export of recruiting records and activity history.",
        requested_by_user_id="recruiter_alpha",
    )

    class _World:
        async def get_candidate(self, candidate_id):
            calls.append(("candidate", candidate_id))
            return candidate if candidate_id == candidate.candidate_id else None

        async def create_data_subject_request(self, created):
            calls.append(("create", created.organization_id, created.request_type))
            return request

        async def get_data_subject_request(self, organization_id, request_id):
            calls.append(("get", organization_id, request_id))
            return request if (organization_id, request_id) == ("org_alpha", request.data_subject_request_id) else None

        async def decide_data_subject_request(self, organization_id, request_id, **kwargs):
            calls.append(("decide", organization_id, request_id, kwargs["status"].value))
            request.status = kwargs["status"]
            request.reviewed_by_user_id = kwargs["reviewed_by_user_id"]
            return request

        async def create_audit_export_manifest(self, manifest):
            calls.append(("manifest", manifest.organization_id, manifest.filters["kind"]))
            manifest.status = AuditExportStatus.READY
            return manifest

        async def link_data_subject_request_artifact(self, organization_id, request_id, **kwargs):
            calls.append(("link", organization_id, request_id, kwargs["audit_export_id"]))
            request.audit_export_id = kwargs["audit_export_id"]
            return request

        async def record_activity(self, activity):
            calls.append(("activity", activity.organization_id, activity.event_type, activity.entity_id))
            return activity

    class _Governance:
        async def list_events(self, organization_id, subject_id, limit):
            calls.append(("events", organization_id, subject_id, limit))
            return []

        async def emit(self, event):
            calls.append(("event", event.event_type.value, event.organization_id))
            return event

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())
    recruiter = SimpleNamespace(user_id="recruiter_alpha", organization_id="org_alpha", role=Role.RECRUITER)
    admin = SimpleNamespace(user_id="admin_alpha", organization_id="org_alpha", role=Role.ADMIN)

    created = asyncio.run(server.create_data_subject_request(
        server.CreateDataSubjectRequestRequest(
            candidate_id=candidate.candidate_id,
            request_type="access",
            request_summary=request.request_summary,
        ),
        recruiter,
    ))
    decided = asyncio.run(server.decide_data_subject_request(
        request.data_subject_request_id,
        server.DecideDataSubjectRequestRequest(decision="approved", note="Identity and request scope verified."),
        admin,
    ))

    assert created["organization_id"] == "org_alpha"
    assert decided["status"] == DataSubjectRequestStatus.APPROVED.value
    assert decided["audit_export_id"].startswith("auditexp_")
    assert ("create", "org_alpha", "access") in calls
    assert ("manifest", "org_alpha", "data_subject_access") in calls
    assert ("activity", "org_alpha", "data_subject_request.requested", candidate.candidate_id) in calls
    assert ("activity", "org_alpha", "data_subject_request.decided", candidate.candidate_id) in calls


def test_data_subject_erasure_cannot_be_marked_fulfilled_before_policy_gated_retention_execution(monkeypatch):
    request = DataSubjectRequest(
        organization_id="org_alpha",
        candidate_id="cand_alpha",
        request_type="erasure",
        request_summary="Candidate requested erasure of personal recruiting data after identity verification.",
        requested_by_user_id="recruiter_alpha",
        status=DataSubjectRequestStatus.APPROVED,
        retention_case_id="ret_alpha",
    )

    class _World:
        async def get_data_subject_request(self, organization_id, request_id):
            return request if (organization_id, request_id) == ("org_alpha", request.data_subject_request_id) else None

        async def get_retention_case(self, organization_id, retention_case_id):
            return RetentionCase(
                organization_id=organization_id,
                retention_case_id=retention_case_id,
                subject_type="candidate",
                subject_id="cand_alpha",
                requested_action="erase",
                reason="Approved data-subject erasure request.",
                requested_by_user_id="admin_alpha",
                status=RetentionCaseStatus.APPROVED_FOR_ERASURE,
            )

    monkeypatch.setattr(server, "world", _World())
    admin = SimpleNamespace(user_id="admin_alpha", organization_id="org_alpha", role=Role.ADMIN)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.fulfill_data_subject_request(request.data_subject_request_id, admin))

    assert exc.value.status_code == 409
    assert "policy-gated retention execution" in exc.value.detail


def test_application_stage_movement_is_recruiter_controlled_and_terminal_outcomes_are_governed(monkeypatch):
    calls = []
    pipeline = server.Pipeline(
        organization_id="org_alpha",
        name="Standard hiring",
        stages=[
            server.PipelineStageDefinition(stage_id="stage_applied", name="Applied", order=0, is_default=True),
            server.PipelineStageDefinition(stage_id="stage_interview", name="Interview", order=1),
            server.PipelineStageDefinition(stage_id="stage_hired", name="Hired", order=2, category="terminal_hired"),
        ],
    )
    application = server.Application(
        organization_id="org_alpha",
        application_id="app_alpha",
        candidate_id="cand_alpha",
        pipeline_id=pipeline.pipeline_id,
        current_stage_id="stage_applied",
        current_stage_name="Applied",
    )

    class _World:
        async def get_application(self, organization_id, application_id):
            return application if (organization_id, application_id) == ("org_alpha", "app_alpha") else None

        async def get_pipeline(self, organization_id, pipeline_id):
            return pipeline if (organization_id, pipeline_id) == ("org_alpha", pipeline.pipeline_id) else None

        async def upsert_application(self, updated):
            calls.append(("upsert", updated.current_stage_name))
            return updated

        async def record_activity(self, activity):
            calls.append(("activity", activity.event_type, activity.payload["to"]))

    class _Governance:
        async def emit(self, event):
            calls.append(("event", event.event_type.value, event.payload["to"]))

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())
    recruiter = SimpleNamespace(user_id="recruiter_alpha", organization_id="org_alpha", role=Role.RECRUITER)
    manager = SimpleNamespace(user_id="manager_alpha", organization_id="org_alpha", role=Role.HIRING_MANAGER)

    with pytest.raises(HTTPException) as forbidden:
        asyncio.run(server.move_ats_application_stage(
            "app_alpha", server.ApplicationStageRequest(stage_id="stage_interview", stage_name="Interview"), manager
        ))
    assert forbidden.value.status_code == 403

    with pytest.raises(HTTPException) as terminal:
        asyncio.run(server.move_ats_application_stage(
            "app_alpha", server.ApplicationStageRequest(stage_id="stage_hired", stage_name="Hired"), recruiter
        ))
    assert terminal.value.status_code == 409
    assert "approval-gated hiring decision" in terminal.value.detail

    moved = asyncio.run(server.move_ats_application_stage(
        "app_alpha", server.ApplicationStageRequest(stage_id="stage_interview", stage_name="Interview"), recruiter
    ))
    assert moved["current_stage_name"] == "Interview"
    assert ("upsert", "Interview") in calls
    assert ("event", "world.application.stage_changed", "Interview") in calls


def test_operational_requisition_request_preserves_complete_hiring_plan_fields():
    request = server.RequisitionCreateRequest(
        title="Senior Product Designer",
        requisition_code="DES-2026-014",
        headcount=2,
        headcount_type="replacement",
        employment_type="full_time",
        seniority="IC4",
        work_arrangement="hybrid",
        location="San Francisco",
        country="United States",
        cost_center="CC-420",
        priority="high",
        compensation={"currency": "USD", "salary_min": 150000, "salary_max": 190000},
        internal_description="Confidential growth hire.",
        public_description="Design our enterprise recruiting experience.",
        required_skills=["Product design", "Research"],
        preferred_skills=["ATS experience"],
        evaluation_plan={"scorecard_required": True},
    )

    assert request.requisition_code == "DES-2026-014"
    assert request.headcount_type == "replacement"
    assert request.work_arrangement == "hybrid"
    assert request.compensation["salary_max"] == 190000
    assert request.evaluation_plan["scorecard_required"] is True

    with pytest.raises(ValueError):
        server.RequisitionCreateRequest(title="Unsafe", work_arrangement="wherever")


def test_offer_draft_is_tenant_scoped_audited_and_never_extended_by_creation(monkeypatch):
    calls = []

    class _World:
        async def upsert_offer(self, offer):
            calls.append(("offer", offer.organization_id, offer.candidate_id, offer.status.value))
            return offer

        async def record_activity(self, activity):
            calls.append(("activity", activity.organization_id, activity.event_type, activity.payload["status"]))

    class _Governance:
        async def emit(self, event):
            calls.append(("event", event.organization_id, event.event_type.value, event.payload["status"]))

    async def _candidate(candidate_id, _user):
        return SimpleNamespace(candidate_id=candidate_id, organization_id="org_alpha")

    async def _job(job_id, _user):
        return SimpleNamespace(job_id=job_id, organization_id="org_alpha")

    monkeypatch.setattr(server, "world", _World())
    monkeypatch.setattr(server, "governance", _Governance())
    monkeypatch.setattr(server, "_scoped_candidate", _candidate)
    monkeypatch.setattr(server, "_scoped_job", _job)
    recruiter = SimpleNamespace(user_id="recruiter_alpha", organization_id="org_alpha", role=Role.RECRUITER)

    result = asyncio.run(server.create_ats_offer_draft(
        server.OfferDraftCreateRequest(candidate_id="cand_alpha", job_id="job_alpha", base_salary=175000, currency="USD"),
        recruiter,
    ))

    assert result["organization_id"] == "org_alpha"
    assert result["status"] == "draft"
    assert ("offer", "org_alpha", "cand_alpha", "draft") in calls
    assert ("event", "org_alpha", "world.offer.draft_created", "draft") in calls
    assert all("extended" not in call for call in calls)


def test_core_ats_lifecycle_creates_canonical_records_and_defers_final_status_to_independent_approval(monkeypatch):
    class _LifecycleWorld:
        def __init__(self):
            self.candidates = {}
            self.requisitions = {}
            self.applications = {}
            self.interviews = {}
            self.scorecards = {}
            self.feedback = {}
            self.offers = {}
            self.decisions = {}
            self.activities = []
            self.pipeline = server.Pipeline(
                organization_id="org_alpha",
                name="Enterprise standard",
                stages=[
                    server.PipelineStageDefinition(stage_id="applied", name="Applied", order=0, is_default=True),
                    server.PipelineStageDefinition(stage_id="screened", name="Screened", order=1),
                    server.PipelineStageDefinition(stage_id="interview", name="Interview", order=2),
                    server.PipelineStageDefinition(stage_id="offer", name="Offer", order=3),
                ],
            )

        async def upsert_candidate(self, candidate):
            self.candidates[candidate.candidate_id] = candidate
            return candidate

        async def upsert_requisition(self, requisition):
            self.requisitions[requisition.requisition_id] = requisition
            return requisition

        async def list_applications(self, organization_id, candidate_id=None, requisition_id=None, **_kwargs):
            return [item for item in self.applications.values() if item.organization_id == organization_id and (not candidate_id or item.candidate_id == candidate_id) and (not requisition_id or item.requisition_id == requisition_id)]

        async def upsert_application(self, application):
            self.applications[application.application_id] = application
            return application

        async def get_application(self, organization_id, application_id):
            item = self.applications.get(application_id)
            return item if item and item.organization_id == organization_id else None

        async def get_pipeline(self, organization_id, pipeline_id):
            return self.pipeline if (organization_id, pipeline_id) == ("org_alpha", self.pipeline.pipeline_id) else None

        async def upsert_interview(self, interview):
            self.interviews[interview.interview_id] = interview
            return interview

        async def get_interview(self, organization_id, interview_id):
            item = self.interviews.get(interview_id)
            return item if item and item.organization_id == organization_id else None

        async def upsert_scorecard(self, scorecard):
            self.scorecards[scorecard.scorecard_id] = scorecard
            return scorecard

        async def get_scorecard(self, organization_id, scorecard_id):
            item = self.scorecards.get(scorecard_id)
            return item if item and item.organization_id == organization_id else None

        async def upsert_interview_feedback(self, feedback):
            self.feedback[feedback.feedback_id] = feedback
            return feedback

        async def upsert_offer(self, offer):
            self.offers[offer.offer_id] = offer
            return offer

        async def list_hiring_decisions(self, organization_id, application_id=None, **_kwargs):
            return [item for item in self.decisions.values() if item.organization_id == organization_id and (not application_id or item.application_id == application_id)]

        async def create_hiring_decision(self, decision):
            self.decisions[decision.hiring_decision_id] = decision
            return decision

        async def record_activity(self, activity):
            self.activities.append(activity)
            return activity

    class _Governance:
        def __init__(self):
            self.approvals = []
            self.events = []

        async def request_approval(self, approval):
            self.approvals.append(approval)
            return approval

        async def emit(self, event):
            self.events.append(event)
            return event

    world = _LifecycleWorld()
    governance = _Governance()
    candidate = asyncio.run(world.upsert_candidate(Candidate(organization_id="org_alpha", full_name="Casey Candidate", email="casey@example.test")))
    requisition = asyncio.run(world.upsert_requisition(Requisition(organization_id="org_alpha", title="Platform Engineer")))
    job = SimpleNamespace(job_id="job_alpha", organization_id="org_alpha")

    async def _candidate(candidate_id, _user):
        return candidate if candidate_id == candidate.candidate_id else None

    async def _requisition(requisition_id, _user):
        return requisition if requisition_id == requisition.requisition_id else None

    async def _job(job_id, _user):
        return job if job_id == job.job_id else None

    monkeypatch.setattr(server, "world", world)
    monkeypatch.setattr(server, "governance", governance)
    monkeypatch.setattr(server, "_scoped_candidate", _candidate)
    monkeypatch.setattr(server, "_scoped_requisition", _requisition)
    monkeypatch.setattr(server, "_scoped_job", _job)
    recruiter = SimpleNamespace(user_id="recruiter_alpha", organization_id="org_alpha", role=Role.RECRUITER)

    application = asyncio.run(server.create_ats_application(server.ApplicationCreateRequest(
        candidate_id=candidate.candidate_id,
        requisition_id=requisition.requisition_id,
        job_id=job.job_id,
        pipeline_id=world.pipeline.pipeline_id,
        current_stage_id="applied",
    ), recruiter))
    for stage_id, stage_name in (("screened", "Screened"), ("interview", "Interview"), ("offer", "Offer")):
        asyncio.run(server.move_ats_application_stage(application["application_id"], server.ApplicationStageRequest(stage_id=stage_id, stage_name=stage_name), recruiter))
    interview = asyncio.run(server.create_ats_interview(server.InterviewCreateRequest(
        application_id=application["application_id"], candidate_id=candidate.candidate_id, scheduled_at="2026-09-01T10:00:00+00:00"
    ), recruiter))
    scorecard = asyncio.run(server.create_ats_scorecard(server.ScorecardCreateRequest(
        name="Platform engineering evidence", requisition_id=requisition.requisition_id, competencies=[{"name": "Systems judgment"}]
    ), recruiter))
    feedback = asyncio.run(server.create_ats_interview_feedback(interview["interview_id"], server.InterviewFeedbackCreateRequest(
        scorecard_id=scorecard["scorecard_id"], recommendation="strong_yes", ratings={"Systems judgment": 4.0}
    ), recruiter))
    offer = asyncio.run(server.create_ats_offer_draft(server.OfferDraftCreateRequest(
        candidate_id=candidate.candidate_id, job_id=job.job_id, base_salary=175000, currency="USD"
    ), recruiter))
    decision = asyncio.run(server.request_ats_hiring_decision(server.HiringDecisionCreateRequest(
        application_id=application["application_id"], outcome="hire", rationale="Structured panel evidence supports a final hire decision."
    ), recruiter))

    persisted_application = world.applications[application["application_id"]]
    assert persisted_application.current_stage_name == "Offer"
    assert persisted_application.status is ApplicationStatus.ACTIVE
    assert interview["application_id"] == application["application_id"]
    assert feedback["interview_id"] == interview["interview_id"]
    assert offer["status"] == "draft"
    assert decision["status"] == "awaiting_approval"
    assert len(governance.approvals) == 1
    assert governance.approvals[0].requested_by == recruiter.user_id


def test_configured_application_questions_accept_only_canonical_required_answers():
    questions = server._normalized_application_questions([
        {"question_id": "work_authorization", "label": "Authorized to work?", "type": "single_select", "required": True, "options": ["Yes", "No"]},
        {"question_id": "portfolio", "label": "Portfolio", "type": "text", "required": False},
    ])

    accepted = server._validated_application_answers(questions, [
        {"question_id": "work_authorization", "value": "Yes"},
        {"question_id": "portfolio", "value": "https://portfolio.example.test"},
    ])
    assert accepted[0]["question_id"] == "work_authorization"
    assert accepted[0]["value"] == "Yes"

    with pytest.raises(HTTPException) as missing_required:
        server._validated_application_answers(questions, [])
    assert missing_required.value.status_code == 422

    with pytest.raises(HTTPException) as undeclared_question:
        server._validated_application_answers(questions, [{"question_id": "untrusted", "value": "value"}])
    assert undeclared_question.value.status_code == 400


def test_source_performance_uses_only_tenant_loaded_candidates_and_applications(monkeypatch):
    class _World:
        async def list_applications(self, organization_id):
            assert organization_id == "org_alpha"
            return [
                SimpleNamespace(candidate_id="cand_a", source="career_site", current_stage_name="Applied", status="active"),
                SimpleNamespace(candidate_id="cand_a", source="career_site", current_stage_name="Hired", status="active"),
                SimpleNamespace(candidate_id="cand_b", source="", current_stage_name="Rejected", status="rejected"),
            ]

        async def list_candidates(self, organization_id):
            assert organization_id == "org_alpha"
            return [SimpleNamespace(candidate_id="cand_a", source="career_site"), SimpleNamespace(candidate_id="cand_b", source="referral")]

    monkeypatch.setattr(server, "world", _World())
    recruiter = SimpleNamespace(user_id="recruiter_alpha", organization_id="org_alpha", role=Role.RECRUITER)
    result = asyncio.run(server.get_ats_source_performance(recruiter))

    assert result["organization_id"] == "org_alpha"
    assert result["sources"] == [
        {"source": "career_site", "applications": 2, "active": 1, "hired": 1, "rejected": 0},
        {"source": "referral", "applications": 1, "active": 0, "hired": 0, "rejected": 1},
    ]


def test_benchmarked_ats_catalog_routes_preserve_governance_and_record_only_delivery_boundaries():
    source = Path(__file__).parents[1].joinpath("server.py").read_text()

    assert '@app.put("/api/ats/requisitions/{requisition_id}/application-questions")' in source
    assert "Application questions cannot change after applications are received" in source
    assert '@app.post("/api/ats/disposition-reasons", status_code=201)' in source
    assert "_require_role(user, Role.ADMIN)" in source
    assert '@app.post("/api/ats/communication-templates", status_code=201)' in source
    assert '"delivery_state": "record_only_provider_not_configured"' in source
    assert '@app.get("/api/ats/analytics/source-performance")' in source
    assert "disposition_reason_code" in source
