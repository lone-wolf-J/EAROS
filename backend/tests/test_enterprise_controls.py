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
from foundation import AuditExportStatus, ExecutionStatus, RetentionCaseStatus, Role
from platform_core.capabilities import build_default_registry
from platform_core.governance import Governance
from platform_core.policy import PolicyEngine
from platform_core.runtime import Runtime
from platform_core.world import AuditExportManifest, Candidate, Requisition, RetentionCase
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
    admin_result = asyncio.run(server.enterprise_administration_readiness(SimpleNamespace(role=Role.ADMIN)))

    assert {role["id"] for role in admin_result["roles"]} == {role.value for role in Role}
    assert admin_result["sso_saml"]["status"] == "not_configured"
    assert "secrets" not in admin_result["sso_saml"]

    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.enterprise_administration_readiness(SimpleNamespace(role=Role.RECRUITER)))
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
