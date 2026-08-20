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
    HiringDecision,
    Interview,
    InterviewFeedback,
    OnboardingHandoff,
    Offer,
    Pipeline,
    PipelineStageDefinition,
    Requisition,
    ResumeDocument,
    RetentionCase,
    Scorecard,
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


class _LifecycleCursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, field, direction):
        self.docs.sort(key=lambda doc: doc.get(field, ""), reverse=direction < 0)
        return self

    async def to_list(self, limit):
        return [dict(doc) for doc in self.docs[:limit]]


class _LifecycleCollection:
    def __init__(self):
        self.docs = []

    @staticmethod
    def _matches(document, query):
        return all(document.get(key) == value for key, value in query.items())

    async def insert_one(self, document):
        self.docs.append(dict(document))

    async def update_one(self, query, update, upsert=False):
        document = next((doc for doc in self.docs if self._matches(doc, query)), None)
        if document is None and upsert:
            document = dict(query)
            self.docs.append(document)
        if document is None:
            return type("Result", (), {"matched_count": 0})()
        document.update(update.get("$set", {}))
        for key, value in update.get("$push", {}).items():
            document.setdefault(key, []).append(value)
        return type("Result", (), {"matched_count": 1})()

    def find(self, query, _projection=None):
        return _LifecycleCursor([doc for doc in self.docs if self._matches(doc, query)])

    async def find_one(self, query, _projection=None):
        document = next((doc for doc in self.docs if self._matches(doc, query)), None)
        return dict(document) if document else None


class _LifecycleDatabase:
    def __init__(self):
        for collection_name in (
            "candidates", "pipelines", "requisitions", "applications", "interviews",
            "scorecards", "interview_feedback", "offers", "hiring_decisions",
        ):
            setattr(self, collection_name, _LifecycleCollection())


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


def test_candidate_crm_search_filters_within_tenant_by_query_tag_source_and_fit_score():
    matching = _candidate(
        "org_a",
        full_name="Grace Hopper",
        source="referral",
        source_detail="engineering network",
        tags=["Priority", "Platform"],
        skills=["Python", "Compilers"],
        fit_score=0.91,
    )
    low_fit = _candidate(
        "org_a", full_name="Grace Low", source="referral", tags=["Priority"], fit_score=0.4
    )
    other_tenant = _candidate(
        "org_b", full_name="Grace Hopper", source="referral", tags=["Priority"], fit_score=0.99
    )
    world = WorldState(_FakeDatabase([
        matching.model_dump(), low_fit.model_dump(), other_tenant.model_dump()
    ]))

    results = asyncio.run(world.search_candidates(
        "org_a", query="grace compilers", tags=["priority"], source="referral", minimum_fit_score=0.8
    ))

    assert [candidate.candidate_id for candidate in results] == [matching.candidate_id]


def test_candidate_crm_update_scopes_source_tags_and_archive_mutations_to_active_tenant():
    candidate_a = _candidate("org_a", tags=["Existing"], source="manual")
    candidate_b = _candidate("org_b", tags=["Other"], source="agency")
    database = _RetentionDatabase([candidate_a.model_dump(), candidate_b.model_dump()], [], [])
    world = WorldState(database)

    updated = asyncio.run(world.update_candidate_crm(
        "org_a",
        candidate_a.candidate_id,
        tags=["Existing", "Priority", "Priority"],
        source="referral",
        source_detail="employee referral",
        archived_at="2026-08-19T12:00:00+00:00",
    ))
    wrong_tenant = asyncio.run(world.update_candidate_crm(
        "org_a", candidate_b.candidate_id, source="manual"
    ))

    assert updated and updated.tags == ["Existing", "Priority"]
    assert updated.source == "referral"
    assert updated.source_detail == "employee referral"
    assert updated.archived_at == "2026-08-19T12:00:00+00:00"
    assert wrong_tenant is None
    assert database.candidates.docs[1]["source"] == "agency"


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


def test_persistence_backed_core_recruiting_lifecycle_remains_tenant_scoped_and_requires_independent_resolution():
    database = _LifecycleDatabase()
    world = WorldState(database)
    pipeline = Pipeline(
        organization_id="org_a",
        name="Engineering lifecycle",
        stages=[
            PipelineStageDefinition(name="Applied", order=0, is_default=True),
            PipelineStageDefinition(name="Screened", order=1),
            PipelineStageDefinition(name="Interview", order=2),
            PipelineStageDefinition(name="Offer", order=3),
        ],
    )
    candidate = _candidate("org_a")
    requisition = Requisition(
        organization_id="org_a", title="Principal Engineer", job_id=candidate.job_id, pipeline_id=pipeline.pipeline_id
    )
    application = Application(
        organization_id="org_a", candidate_id=candidate.candidate_id,
        requisition_id=requisition.requisition_id, pipeline_id=pipeline.pipeline_id,
        current_stage_id=pipeline.stages[0].stage_id, current_stage_name="Applied",
    )
    interview = Interview(
        organization_id="org_a", application_id=application.application_id,
        candidate_id=candidate.candidate_id, scheduled_at="2026-08-20T10:00:00+00:00",
        interviewer_ids=["usr_manager"],
    )
    scorecard = Scorecard(
        organization_id="org_a", requisition_id=requisition.requisition_id,
        name="Engineering scorecard", competencies=[{"name": "Systems design", "weight": 1}],
    )
    feedback = InterviewFeedback(
        organization_id="org_a", interview_id=interview.interview_id,
        scorecard_id=scorecard.scorecard_id, interviewer_id="usr_manager",
        recommendation="strong_yes", ratings={"systems_design": 5.0},
    )
    offer = Offer(
        organization_id="org_a", candidate_id=candidate.candidate_id, job_id=candidate.job_id,
        base_salary=180000, currency="USD",
    )
    decision = HiringDecision(
        organization_id="org_a", application_id=application.application_id,
        candidate_id=candidate.candidate_id, requisition_id=requisition.requisition_id,
        outcome="hire", rationale="Interview evidence and scorecard support the hiring recommendation.",
        requested_by_user_id="usr_recruiter", approval_id="apr_independent",
    )

    async def run_lifecycle():
        await world.upsert_pipeline(pipeline)
        await world.upsert_candidate(candidate)
        await world.upsert_requisition(requisition)
        await world.upsert_application(application)
        await world.upsert_interview(interview)
        await world.upsert_scorecard(scorecard)
        await world.upsert_interview_feedback(feedback)
        await world.upsert_offer(offer)
        await world.create_hiring_decision(decision)
        pre_resolution = await world.get_application("org_a", application.application_id)
        assert pre_resolution and pre_resolution.status is ApplicationStatus.ACTIVE
        resolved = await world.resolve_hiring_decision(
            "org_a", decision.hiring_decision_id, approval_id="apr_independent",
            status="effective", resolved_by_user_id="usr_admin",
        )
        applied = await world.apply_hiring_decision_application_status("org_a", resolved)
        return resolved, applied

    resolved, applied = asyncio.run(run_lifecycle())

    assert resolved.status == "effective"
    assert resolved.resolved_by_user_id == "usr_admin"
    assert applied and applied.status is ApplicationStatus.HIRED
    assert applied.stage_history[-1]["reason"] == "approved_hiring_decision"
    assert len(database.interview_feedback.docs) == 1
    assert len(database.offers.docs) == 1
    assert asyncio.run(world.get_application("org_b", application.application_id)) is None
