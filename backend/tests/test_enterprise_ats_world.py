"""Unit-level contracts for the enterprise ATS records introduced in EAROS world state."""
from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from foundation import (
    ApplicationStatus,
    ConsentStatus,
    InterviewStatus,
    OnboardingHandoffStatus,
    RetentionCaseStatus,
    RequisitionStatus,
)
from platform_core.world import (
    Application,
    Candidate,
    CandidateConsent,
    Interview,
    OnboardingHandoff,
    Pipeline,
    PipelineStageDefinition,
    Requisition,
    ResumeDocument,
    RetentionCase,
    WorldState,
)


class _Cursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, *_args):
        return self

    async def to_list(self, limit):
        return self.docs[:limit]


class _CandidatesCollection:
    def __init__(self, docs):
        self.docs = docs
        self.last_query = None

    def find(self, query, _projection):
        self.last_query = query
        return _Cursor([doc for doc in self.docs if doc["organization_id"] == query["organization_id"]])


class _FakeDatabase:
    def __init__(self, docs):
        self.candidates = _CandidatesCollection(docs)


class _HandoffsCollection:
    def __init__(self, docs):
        self.docs = docs
        self.last_query = None

    def find(self, query, _projection):
        self.last_query = query
        return _Cursor([
            doc for doc in self.docs
            if doc["organization_id"] == query["organization_id"]
            and ("status" not in query or doc["status"] == query["status"])
        ])


class _HandoffDatabase:
    def __init__(self, docs):
        self.onboarding_handoffs = _HandoffsCollection(docs)


class _RetentionCollection:
    def __init__(self, docs):
        self.docs = docs

    @staticmethod
    def _matches(document, query):
        return all(document.get(key) == value for key, value in query.items())

    async def find_one(self, query, _projection=None):
        return next((dict(doc) for doc in self.docs if self._matches(doc, query)), None)

    async def update_one(self, query, update, upsert=False):
        document = next((doc for doc in self.docs if self._matches(doc, query)), None)
        if document is None and upsert:
            document = dict(query)
            self.docs.append(document)
        if document is None:
            return type("Result", (), {"matched_count": 0})()
        document.update(update.get("$set", {}))
        return type("Result", (), {"matched_count": 1})()


class _RetentionDatabase:
    def __init__(self, candidates, applications, cases):
        self.candidates = _RetentionCollection(candidates)
        self.applications = _RetentionCollection(applications)
        self.retention_cases = _RetentionCollection(cases)


def _candidate(organization_id: str, **overrides):
    payload = {
        "organization_id": organization_id,
        "job_id": "job_01",
        "full_name": "Ada Lovelace",
        "email": "ada@example.com",
        "location": "London",
        "country": "GB",
        "current_title": "Engineer",
        "current_company": "Analytical Engines",
        "years_experience": 5,
        "expected_salary": 100000,
        "currency": "GBP",
    }
    payload.update(overrides)
    return Candidate(**payload)


def test_enterprise_records_require_tenant_scope_and_preserve_status_contracts():
    pipeline = Pipeline(
        organization_id="org_a",
        name="Engineering",
        stages=[
            PipelineStageDefinition(name="Applied", order=0, is_default=True),
            PipelineStageDefinition(name="Hired", order=1, category="terminal_hired"),
        ],
    )
    requisition = Requisition(
        organization_id="org_a",
        title="Staff Engineer",
        approval_status=RequisitionStatus.PENDING_APPROVAL,
        pipeline_id=pipeline.pipeline_id,
    )
    application = Application(
        organization_id="org_a",
        candidate_id="cand_01",
        requisition_id=requisition.requisition_id,
        pipeline_id=pipeline.pipeline_id,
        current_stage_id=pipeline.stages[0].stage_id,
        current_stage_name="Applied",
    )
    consent = CandidateConsent(
        organization_id="org_a",
        candidate_id="cand_01",
        purpose="recruiting",
        status=ConsentStatus.GRANTED,
    )
    interview = Interview(
        organization_id="org_a",
        application_id=application.application_id,
        candidate_id="cand_01",
        scheduled_at="2026-08-19T10:00:00+00:00",
        status=InterviewStatus.SCHEDULED,
    )
    resume = ResumeDocument(
        organization_id="org_a",
        candidate_id="cand_01",
        file_name="ada-resume.pdf",
    )

    assert application.status is ApplicationStatus.ACTIVE
    assert requisition.approval_status is RequisitionStatus.PENDING_APPROVAL
    assert consent.status is ConsentStatus.GRANTED
    assert interview.status is InterviewStatus.SCHEDULED
    assert resume.is_primary is True

    with pytest.raises(ValidationError):
        Application(candidate_id="cand_01")


def test_duplicate_lookup_normalizes_identity_and_never_queries_across_tenants():
    org_a_candidate = _candidate("org_a", email="Ada.Lovelace@Example.com", phone="+44 (0) 20 7000 0000")
    org_b_candidate = _candidate("org_b", email="ada@example.com", linkedin_url="https://linkedin.com/in/ada")
    fake_db = _FakeDatabase([org_a_candidate.model_dump(), org_b_candidate.model_dump()])
    world = WorldState(fake_db)

    email_match = asyncio.run(world.find_duplicate_candidate("org_a", email="ada.lovelace@example.COM"))
    phone_match = asyncio.run(world.find_duplicate_candidate("org_a", phone="4402070000000"))
    cross_tenant_match = asyncio.run(world.find_duplicate_candidate("org_a", linkedin_url="https://linkedin.com/in/ada"))

    assert fake_db.candidates.last_query == {"organization_id": "org_a"}
    assert email_match and email_match.candidate_id == org_a_candidate.candidate_id
    assert phone_match and phone_match.candidate_id == org_a_candidate.candidate_id
    assert cross_tenant_match is None


def test_onboarding_handoff_is_tenant_scoped_and_carries_only_routing_metadata():
    handoff_a = OnboardingHandoff(
        organization_id="org_a",
        offer_id="offer_a",
        candidate_id="cand_a",
        job_id="job_a",
        destination_system="hris_connector",
        checklist=[{"key": "provision_account", "owner": "people_ops", "status": "pending"}],
        status=OnboardingHandoffStatus.READY_FOR_HANDOFF,
    )
    handoff_b = OnboardingHandoff(
        organization_id="org_b",
        offer_id="offer_b",
        candidate_id="cand_b",
        job_id="job_b",
    )
    world = WorldState(_HandoffDatabase([handoff_a.model_dump(), handoff_b.model_dump()]))

    visible = asyncio.run(world.list_onboarding_handoffs("org_a"))

    assert len(visible) == 1
    assert visible[0].onboarding_handoff_id == handoff_a.onboarding_handoff_id
    assert visible[0].status is OnboardingHandoffStatus.READY_FOR_HANDOFF
    assert "payroll" not in visible[0].model_dump()
    assert "background_check_document" not in visible[0].model_dump()


def test_retention_execution_archives_or_redacts_only_approved_nonheld_tenant_subjects():
    candidate = _candidate("org_a")
    archive_case = RetentionCase(
        organization_id="org_a",
        subject_type="candidate",
        subject_id=candidate.candidate_id,
        requested_action="archive",
        reason="Retention period expired after recruiting closeout.",
        requested_by_user_id="usr_admin",
        status=RetentionCaseStatus.APPROVED_FOR_ARCHIVE,
    )
    erase_case = RetentionCase(
        organization_id="org_a",
        subject_type="candidate",
        subject_id=candidate.candidate_id,
        requested_action="erase",
        reason="Data-subject deletion request approved after legal review.",
        requested_by_user_id="usr_admin",
        status=RetentionCaseStatus.APPROVED_FOR_ERASURE,
    )
    world = WorldState(_RetentionDatabase(
        [candidate.model_dump()], [], [archive_case.model_dump(), erase_case.model_dump()]
    ))

    archived = asyncio.run(world.execute_retention_case("org_a", archive_case.retention_case_id, expected_action="archive"))
    assert archived and archived.status is RetentionCaseStatus.COMPLETED
    archived_candidate = asyncio.run(world.get_candidate_for_organization("org_a", candidate.candidate_id))
    assert archived_candidate and archived_candidate.archived_at

    erased = asyncio.run(world.execute_retention_case("org_a", erase_case.retention_case_id, expected_action="erase"))
    assert erased and erased.status is RetentionCaseStatus.COMPLETED
    redacted_candidate = asyncio.run(world.get_candidate_for_organization("org_a", candidate.candidate_id))
    assert redacted_candidate and redacted_candidate.full_name == "Erased candidate"
    assert redacted_candidate.email is None
    assert redacted_candidate.skills == []
    assert redacted_candidate.erased_at


def test_retention_execution_blocks_legal_hold_and_wrong_tenant_access():
    candidate = _candidate("org_a")
    held_case = RetentionCase(
        organization_id="org_a",
        subject_type="candidate",
        subject_id=candidate.candidate_id,
        requested_action="erase",
        reason="Potential deletion request subject to an active legal hold.",
        requested_by_user_id="usr_admin",
        legal_hold=True,
        status=RetentionCaseStatus.APPROVED_FOR_ERASURE,
    )
    world = WorldState(_RetentionDatabase([candidate.model_dump()], [], [held_case.model_dump()]))

    with pytest.raises(ValueError, match="legal hold"):
        asyncio.run(world.execute_retention_case("org_a", held_case.retention_case_id, expected_action="erase"))
    assert asyncio.run(world.execute_retention_case("org_b", held_case.retention_case_id, expected_action="erase")) is None
