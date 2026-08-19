import asyncio
from copy import deepcopy

import pytest

from platform_core.capabilities import (
    CapabilityContext,
    build_default_registry,
    cap_analyze_resume,
    cap_draft_outreach,
    cap_match_requisition,
    cap_prepare_job_publication,
    cap_source_requisition_prospects,
)
from platform_core.integrations import list_job_distribution_adapters
from platform_core.governance import Governance
from platform_core.planner import Planner
from platform_core.policy import Policy, PolicyEngine
from platform_core.runtime import ExecutionRecord, PlanStep, Runtime
from foundation import ConsentStatus, DomainEvent, EventType, ExecutionStatus
from foundation import RetentionCaseStatus
from platform_core.world import Candidate, CandidateConsent, Job, Requisition, ResumeDocument, RetentionCase


class FakeATSWorld:
    def __init__(self):
        self.job = Job(
            organization_id="org_alpha",
            department_id="dept_engineering",
            title="Platform Engineer",
            level="IC4",
            location="Remote",
            country="USA",
            salary_min=140000,
            salary_max=180000,
            currency="USD",
            required_skills=["Python", "Kubernetes", "AWS"],
            business_impact="Deliver the organization's core platform.",
            hiring_manager="usr_manager",
        )
        self.requisition = Requisition(
            organization_id="org_alpha",
            title="Platform Engineer",
            job_id=self.job.job_id,
            hiring_plan={"required_skills": ["Python", "Kubernetes", "AWS"]},
        )
        self.candidates = [
            Candidate(
                organization_id="org_alpha",
                job_id=self.job.job_id,
                full_name="Ada Lovelace",
                skills=["Python", "Kubernetes", "AWS"],
                years_experience=9,
            ),
            Candidate(
                organization_id="org_alpha",
                job_id=self.job.job_id,
                full_name="Grace Hopper",
                skills=["Python"],
                years_experience=6,
            ),
        ]
        self.consents = {
            self.candidates[0].candidate_id: [CandidateConsent(
                organization_id="org_alpha",
                candidate_id=self.candidates[0].candidate_id,
                purpose="recruiting",
                status=ConsentStatus.GRANTED,
            )],
            self.candidates[1].candidate_id: [CandidateConsent(
                organization_id="org_alpha",
                candidate_id=self.candidates[1].candidate_id,
                purpose="recruiting",
                status=ConsentStatus.REVOKED,
            )],
        }
        self.resumes = {
            self.candidates[0].candidate_id: [ResumeDocument(
                organization_id="org_alpha",
                candidate_id=self.candidates[0].candidate_id,
                file_name="ada-lovelace.pdf",
                parse_status="parsed",
                parsed_profile={
                    "skills": ["Python", "Kubernetes", "AWS"],
                    "experience": [{"title": "Principal Engineer", "company": "Analytical Engines"}],
                    "education": [{"institution": "University of London"}],
                },
            )],
        }

    async def get_requisition(self, organization_id, requisition_id):
        if organization_id == "org_alpha" and requisition_id == self.requisition.requisition_id:
            return self.requisition
        return None

    async def get_job_for_organization(self, organization_id, job_id):
        if organization_id == "org_alpha" and job_id == self.job.job_id:
            return self.job
        return None

    async def list_candidates(self, organization_id, **_):
        return self.candidates if organization_id == "org_alpha" else []

    async def get_candidate_for_organization(self, organization_id, candidate_id):
        if organization_id != "org_alpha":
            return None
        return next((candidate for candidate in self.candidates if candidate.candidate_id == candidate_id), None)

    async def list_candidate_consents(self, organization_id, candidate_id):
        if organization_id != "org_alpha":
            return []
        return self.consents.get(candidate_id, [])

    async def list_resumes(self, organization_id, candidate_id):
        if organization_id != "org_alpha":
            return []
        return self.resumes.get(candidate_id, [])

    async def list_applications(self, organization_id, requisition_id=None):
        return []


class RetentionCapabilityWorld(FakeATSWorld):
    def __init__(self):
        super().__init__()
        self.retention_case = RetentionCase(
            organization_id="org_alpha",
            subject_type="candidate",
            subject_id=self.candidates[0].candidate_id,
            requested_action="erase",
            reason="Data-subject retention request has completed enterprise review.",
            requested_by_user_id="usr_admin",
            status=RetentionCaseStatus.APPROVED_FOR_ERASURE,
        )
        self.executed_actions = []

    async def create_retention_case(self, retention_case):
        self.retention_case = retention_case
        return retention_case

    async def decide_retention_case(self, organization_id, retention_case_id, *, status, reviewed_by_user_id, decision_note=None):
        if organization_id != "org_alpha" or retention_case_id != self.retention_case.retention_case_id:
            return None
        self.retention_case.status = status
        self.retention_case.reviewed_by_user_id = reviewed_by_user_id
        self.retention_case.decision_note = decision_note
        return self.retention_case

    async def execute_retention_case(self, organization_id, retention_case_id, *, expected_action):
        if organization_id != "org_alpha" or retention_case_id != self.retention_case.retention_case_id:
            return None
        self.executed_actions.append(expected_action)
        subject = self.candidates[0]
        if expected_action == "archive":
            subject.archived_at = "2026-08-19T00:00:00+00:00"
        else:
            subject.full_name = "Redacted candidate"
            subject.email = None
            subject.phone = None
            subject.skills = []
            subject.notes = []
            subject.erased_at = "2026-08-19T00:00:00+00:00"
        self.retention_case.status = RetentionCaseStatus.COMPLETED
        return self.retention_case


class MemoryResult:
    def __init__(self, matched_count=0):
        self.matched_count = matched_count


class MemoryCursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, field, direction):
        self.docs.sort(key=lambda item: item.get(field, ""), reverse=direction < 0)
        return self

    async def to_list(self, limit):
        return deepcopy(self.docs[:limit])


class MemoryCollection:
    def __init__(self):
        self.docs = []

    @staticmethod
    def _matches(doc, query):
        return all(doc.get(key) == value for key, value in query.items())

    async def insert_one(self, document):
        self.docs.append(deepcopy(document))

    async def update_one(self, query, update, upsert=False):
        target = next((doc for doc in self.docs if self._matches(doc, query)), None)
        if not target and upsert:
            target = dict(query)
            self.docs.append(target)
        if not target:
            return MemoryResult()
        target.update(deepcopy(update.get("$set", {})))
        for key, value in update.get("$setOnInsert", {}).items():
            target.setdefault(key, deepcopy(value))
        return MemoryResult(1)

    def find(self, query, projection=None):
        return MemoryCursor([doc for doc in self.docs if self._matches(doc, query)])

    async def find_one(self, query, projection=None):
        doc = next((doc for doc in self.docs if self._matches(doc, query)), None)
        return deepcopy(doc) if doc else None


class MemoryDB:
    def __init__(self):
        self.policies = MemoryCollection()
        self.events = MemoryCollection()
        self.approvals = MemoryCollection()
        self.executions = MemoryCollection()


def runtime_for_publication(world):
    db = MemoryDB()
    governance = Governance(db)
    policy = PolicyEngine(db, governance)
    runtime = Runtime(db, world, build_default_registry(), policy, governance)
    return runtime, policy, governance


def context(world):
    return CapabilityContext(
        organization_id="org_alpha",
        user_id="usr_recruiter",
        execution_id="exe_test",
        correlation_id="cor_test",
        world=world,
    )


def test_registry_exposes_governed_enterprise_ats_capabilities():
    ids = {spec.capability_id for spec in build_default_registry().list_specs()}
    assert {
        "cap.match_requisition",
        "cap.source_requisition_prospects",
        "cap.analyze_resume",
        "cap.score_application",
        "cap.prepare_interview",
        "cap.prepare_job_publication",
        "cap.triage_requisition",
    }.issubset(ids)


def test_requisition_sourcing_is_tenant_scoped_consent_aware_and_read_only():
    world = FakeATSWorld()
    result = asyncio.run(
        cap_source_requisition_prospects(
            {"requisition_id": world.requisition.requisition_id, "limit": 10}, context(world)
        )
    )

    assert result.ok is True
    assert result.output["count"] == 1
    assert result.output["prospects"][0]["candidate_id"] == world.candidates[0].candidate_id
    assert "active recruiting consent" in result.facts[0]
    assert "does not contact" in result.facts[1]


def test_resume_analysis_uses_only_existing_parsed_evidence_and_does_not_mutate_candidate_state():
    world = FakeATSWorld()
    candidate = world.candidates[0]
    original_stage = candidate.stage
    original_skills = list(candidate.skills)

    result = asyncio.run(cap_analyze_resume({"candidate_id": candidate.candidate_id}, context(world)))

    assert result.ok is True
    assert result.output["candidate_id"] == candidate.candidate_id
    assert result.output["extracted_skills"] == ["AWS", "Kubernetes", "Python"]
    assert result.output["requires_human_review"] is True
    assert candidate.stage == original_stage
    assert candidate.skills == original_skills
    assert "distinct from parsing" in result.facts[1]


def test_outreach_draft_requires_recruiting_consent_and_never_sends_a_message():
    world = FakeATSWorld()
    candidate = world.candidates[0]

    draft = asyncio.run(cap_draft_outreach({"candidate_id": candidate.candidate_id}, context(world)))
    assert draft.ok is True
    assert draft.output["delivery_state"] == "draft_only"
    assert "never sends" in draft.facts[1]

    world.consents[candidate.candidate_id][0].status = ConsentStatus.REVOKED
    rejected = asyncio.run(cap_draft_outreach({"candidate_id": candidate.candidate_id}, context(world)))
    assert rejected.ok is False
    assert "active recruiting consent" in rejected.error


def test_deterministic_planner_routes_new_autonomy_goals_to_registered_governed_capabilities():
    world = FakeATSWorld()
    planner = Planner(world, build_default_registry())
    planner.llm_key = ""

    sourcing_plan = asyncio.run(planner.plan(
        "Source consented prospects for this requisition",
        "org_alpha",
        {"requisition_id": world.requisition.requisition_id},
    ))
    resume_plan = asyncio.run(planner.plan(
        "Analyze this candidate's parsed resume",
        "org_alpha",
        {"candidate_id": world.candidates[0].candidate_id},
    ))
    outreach_plan = asyncio.run(planner.plan(
        "Draft outreach for this candidate",
        "org_alpha",
        {"candidate_id": world.candidates[0].candidate_id},
    ))

    assert [step.capability_id for step in sourcing_plan.steps] == ["cap.source_requisition_prospects"]
    assert [step.capability_id for step in resume_plan.steps] == ["cap.analyze_resume"]
    assert [step.capability_id for step in outreach_plan.steps] == ["cap.draft_outreach"]


def test_matching_is_tenant_scoped_ranked_and_read_only():
    world = FakeATSWorld()
    result = asyncio.run(
        cap_match_requisition(
            {"requisition_id": world.requisition.requisition_id, "limit": 10}, context(world)
        )
    )

    assert result.ok is True
    assert result.output["count"] == 2
    assert result.output["matches"][0]["candidate_id"] == world.candidates[0].candidate_id
    assert result.output["matches"][0]["score"] > result.output["matches"][1]["score"]
    assert "does not change candidate" in result.facts[1]


def test_publication_capability_creates_a_draft_packet_not_an_external_post():
    world = FakeATSWorld()
    result = asyncio.run(
        cap_prepare_job_publication(
            {"requisition_id": world.requisition.requisition_id, "boards": ["indeed", "jooble"]},
            context(world),
        )
    )

    assert result.ok is True
    assert result.output["external_publish_state"] == "draft_only"
    assert result.output["targets"] == ["indeed", "jooble"]
    assert "without sending" in result.facts[0]


def test_job_board_catalog_requires_configuration_and_human_approval():
    adapters = list_job_distribution_adapters()
    providers = {adapter.provider for adapter in adapters}

    assert {"linkedin", "dice", "indeed", "ziprecruiter", "jobspikr", "jooble"}.issubset(providers)
    assert all(adapter.configuration_state == "not_configured" for adapter in adapters)
    assert all(adapter.requires_human_approval for adapter in adapters)


def test_publication_packet_is_queued_for_policy_required_human_approval_and_decision_is_audited():
    world = FakeATSWorld()
    runtime, policy, governance = runtime_for_publication(world)
    asyncio.run(policy.upsert_policy(Policy(
        organization_id="org_alpha",
        name="Publication review",
        description="Require a hiring manager before any job-distribution packet is processed.",
        scope="cap.prepare_job_publication",
        requires_human_approval=True,
        required_role_for_approval="hiring_manager",
    )))
    execution = asyncio.run(runtime.execute(ExecutionRecord(
        organization_id="org_alpha", user_id="usr_recruiter", user_role="recruiter",
        goal="Prepare publication", correlation_id="cor_publication_approval",
        steps=[PlanStep(capability_id="cap.prepare_job_publication", inputs={"requisition_id": world.requisition.requisition_id})],
    )))

    assert execution.status == ExecutionStatus.AWAITING_APPROVAL
    assert execution.pending_approvals
    approval_id = execution.pending_approvals[0]
    approvals = asyncio.run(governance.list_approvals("org_alpha", status="pending"))
    assert approvals[0].approval_id == approval_id
    assert approvals[0].context["capability_id"] == "cap.prepare_job_publication"

    decision = asyncio.run(governance.decide_approval(approval_id, "granted", "usr_manager", "Checked target boards."))
    assert decision.status == "granted"
    events = asyncio.run(governance.replay("cor_publication_approval"))
    assert {event.event_type for event in events} >= {
        EventType.EXECUTION_STARTED,
        EventType.POLICY_EVALUATED,
        EventType.APPROVAL_REQUESTED,
        EventType.APPROVAL_GRANTED,
    }


def test_reviewable_publication_packet_writes_execution_and_step_audit_trace_when_policy_allows():
    world = FakeATSWorld()
    runtime, _, governance = runtime_for_publication(world)
    execution = asyncio.run(runtime.execute(ExecutionRecord(
        organization_id="org_alpha", user_id="usr_recruiter", user_role="recruiter",
        goal="Prepare publication", correlation_id="cor_publication_audit",
        steps=[PlanStep(capability_id="cap.prepare_job_publication", inputs={"requisition_id": world.requisition.requisition_id})],
    )))

    assert execution.status == ExecutionStatus.SUCCEEDED
    assert execution.step_results[0]["ok"] is True
    events = asyncio.run(governance.replay("cor_publication_audit"))
    assert {event.event_type for event in events} >= {
        EventType.EXECUTION_STARTED,
        EventType.POLICY_EVALUATED,
        EventType.STEP_STARTED,
        EventType.STEP_COMPLETED,
        EventType.EXECUTION_COMPLETED,
    }


def test_matching_can_be_escalated_to_the_same_human_approval_queue_by_tenant_policy():
    world = FakeATSWorld()
    runtime, policy, governance = runtime_for_publication(world)
    asyncio.run(policy.upsert_policy(Policy(
        organization_id="org_alpha",
        name="Prospect matching review",
        description="Require review before any recruiting team consumes an automated shortlist.",
        scope="cap.match_requisition",
        requires_human_approval=True,
    )))
    execution = asyncio.run(runtime.execute(ExecutionRecord(
        organization_id="org_alpha", user_id="usr_recruiter", user_role="recruiter",
        goal="Match prospects", correlation_id="cor_match_approval",
        steps=[PlanStep(capability_id="cap.match_requisition", inputs={"requisition_id": world.requisition.requisition_id})],
    )))

    assert execution.status == ExecutionStatus.AWAITING_APPROVAL
    approval = asyncio.run(governance.get_approval(execution.pending_approvals[0]))
    assert approval is not None
    assert approval.context["capability_id"] == "cap.match_requisition"


@pytest.mark.parametrize(
    ("capability_id", "inputs"),
    [
        ("cap.score_application", {"application_id": "app_policy_only"}),
        ("cap.source_requisition_prospects", {"requisition_id": "req_policy_only"}),
        ("cap.analyze_resume", {"candidate_id": "cand_policy_only"}),
        ("cap.draft_outreach", {"candidate_id": "cand_policy_only"}),
        ("cap.prepare_interview", {"interview_id": "int_policy_only"}),
        ("cap.triage_requisition", {"requisition_id": "req_policy_only"}),
    ],
)
def test_remaining_ats_capabilities_queue_for_review_and_emit_immutable_trace_when_tenant_policy_requires_it(
    capability_id, inputs
):
    world = FakeATSWorld()
    runtime, policy, governance = runtime_for_publication(world)
    asyncio.run(policy.upsert_policy(Policy(
        organization_id="org_alpha",
        name=f"Review {capability_id}",
        description="Require human review before this governed ATS operation proceeds.",
        scope=capability_id,
        requires_human_approval=True,
    )))
    correlation_id = f"cor_{capability_id.replace('.', '_')}"
    execution = asyncio.run(runtime.execute(ExecutionRecord(
        organization_id="org_alpha", user_id="usr_recruiter", user_role="recruiter",
        goal=f"Review {capability_id}", correlation_id=correlation_id,
        steps=[PlanStep(capability_id=capability_id, inputs=inputs)],
    )))

    assert execution.status == ExecutionStatus.AWAITING_APPROVAL
    persisted = asyncio.run(runtime.get_execution(execution.execution_id))
    assert persisted is not None
    assert persisted.pending_approvals == execution.pending_approvals
    approval = asyncio.run(governance.get_approval(execution.pending_approvals[0]))
    assert approval is not None
    assert approval.context["capability_id"] == capability_id
    events = asyncio.run(governance.replay(correlation_id))
    assert {event.event_type for event in events} >= {
        EventType.EXECUTION_STARTED,
        EventType.POLICY_EVALUATED,
        EventType.APPROVAL_REQUESTED,
    }


def test_retention_erasure_is_queued_by_policy_before_any_mutation_and_emits_a_runtime_trace():
    world = RetentionCapabilityWorld()
    runtime, policy, governance = runtime_for_publication(world)
    asyncio.run(policy.upsert_policy(Policy(
        organization_id="org_alpha",
        name="Retention erasure review",
        description="Require a human approval queue before any profile redaction is executed.",
        scope="cap.execute_retention_erasure",
        requires_human_approval=True,
        required_role_for_approval="admin",
    )))
    execution = asyncio.run(runtime.execute(ExecutionRecord(
        organization_id="org_alpha", user_id="usr_admin", user_role="admin",
        goal="Erase approved retention subject", correlation_id="cor_retention_erasure_review",
        steps=[PlanStep(
            capability_id="cap.execute_retention_erasure",
            inputs={"retention_case_id": world.retention_case.retention_case_id},
            sensitivity="restricted",
        )],
    )))

    assert execution.status == ExecutionStatus.AWAITING_APPROVAL
    assert world.executed_actions == []
    approval = asyncio.run(governance.get_approval(execution.pending_approvals[0]))
    assert approval and approval.context["capability_id"] == "cap.execute_retention_erasure"
    events = asyncio.run(governance.replay("cor_retention_erasure_review"))
    assert {event.event_type for event in events} >= {
        EventType.EXECUTION_STARTED,
        EventType.POLICY_EVALUATED,
        EventType.APPROVAL_REQUESTED,
    }


@pytest.mark.parametrize(
    ("capability_id", "expected_action"),
    [
        ("cap.execute_retention_archive", "archive"),
        ("cap.execute_retention_erasure", "erase"),
    ],
)
def test_retention_execution_has_a_non_overridable_approval_baseline_without_any_tenant_policy(
    capability_id, expected_action
):
    world = RetentionCapabilityWorld()
    world.retention_case.requested_action = expected_action
    world.retention_case.status = (
        RetentionCaseStatus.APPROVED_FOR_ARCHIVE
        if expected_action == "archive"
        else RetentionCaseStatus.APPROVED_FOR_ERASURE
    )
    runtime, _, governance = runtime_for_publication(world)
    correlation_id = f"cor_mandatory_retention_{expected_action}"
    execution = asyncio.run(runtime.execute(ExecutionRecord(
        organization_id="org_alpha", user_id="usr_admin", user_role="admin",
        goal=f"Execute approved retention {expected_action}", correlation_id=correlation_id,
        steps=[PlanStep(
            capability_id=capability_id,
            inputs={"retention_case_id": world.retention_case.retention_case_id},
            sensitivity="restricted",
        )],
    )))

    assert execution.status == ExecutionStatus.AWAITING_APPROVAL
    assert world.executed_actions == []
    approval = asyncio.run(governance.get_approval(execution.pending_approvals[0]))
    assert approval is not None
    assert approval.context["capability_id"] == capability_id
    assert any(
        policy["policy_id"] == "earos.baseline.retention_execution_approval.v1"
        for policy in approval.context["policies"]
    )


@pytest.mark.parametrize(
    ("capability_id", "expected_action"),
    [
        ("cap.execute_retention_archive", "archive"),
        ("cap.execute_retention_erasure", "erase"),
    ],
)
def test_granted_retention_approval_resumes_execution_and_emits_completion_trace(
    capability_id, expected_action
):
    world = RetentionCapabilityWorld()
    world.retention_case.requested_action = expected_action
    world.retention_case.status = (
        RetentionCaseStatus.APPROVED_FOR_ARCHIVE
        if expected_action == "archive"
        else RetentionCaseStatus.APPROVED_FOR_ERASURE
    )
    runtime, _, governance = runtime_for_publication(world)
    execution = asyncio.run(runtime.execute(ExecutionRecord(
        organization_id="org_alpha", user_id="usr_admin", user_role="admin",
        goal=f"Execute retention {expected_action} after approval",
        correlation_id=f"cor_resume_retention_{expected_action}",
        steps=[PlanStep(
            capability_id=capability_id,
            inputs={"retention_case_id": world.retention_case.retention_case_id},
            sensitivity="restricted",
        )],
    )))
    approval_id = execution.pending_approvals[0]
    asyncio.run(governance.decide_approval(approval_id, "granted", "usr_reviewer"))

    resumed = asyncio.run(runtime.resume_after_approval(execution.execution_id, "org_alpha"))

    assert resumed.status == ExecutionStatus.SUCCEEDED
    assert resumed.pending_approvals == []
    assert world.executed_actions == [expected_action]
    events = asyncio.run(governance.replay(resumed.correlation_id))
    assert {event.event_type for event in events} >= {
        EventType.APPROVAL_GRANTED,
        EventType.EXECUTION_RESUMED,
        EventType.EXECUTION_COMPLETED,
    }


@pytest.mark.parametrize(
    ("requested_action", "review_status", "capability_id"),
    [
        ("archive", RetentionCaseStatus.APPROVED_FOR_ARCHIVE, "cap.execute_retention_archive"),
        ("erase", RetentionCaseStatus.APPROVED_FOR_ERASURE, "cap.execute_retention_erasure"),
    ],
)
def test_retention_lifecycle_creates_reviews_approves_resumes_and_mutates_only_after_governance(
    requested_action, review_status, capability_id
):
    world = RetentionCapabilityWorld()
    candidate = world.candidates[0]
    runtime, _, governance = runtime_for_publication(world)
    correlation_id = f"cor_lifecycle_{requested_action}"

    async def run_lifecycle():
        retention_case = await world.create_retention_case(RetentionCase(
            organization_id="org_alpha",
            subject_type="candidate",
            subject_id=candidate.candidate_id,
            requested_action=requested_action,
            reason="Verified retention lifecycle request requires an auditable review and approval flow.",
            requested_by_user_id="usr_admin",
        ))
        await governance.emit(DomainEvent(
            event_type=EventType.RETENTION_CASE_REQUESTED,
            actor="usr_admin",
            subject_type="candidate",
            subject_id=candidate.candidate_id,
            organization_id="org_alpha",
            payload={"retention_case_id": retention_case.retention_case_id, "requested_action": requested_action},
            correlation_id=correlation_id,
        ))
        reviewed = await world.decide_retention_case(
            "org_alpha", retention_case.retention_case_id,
            status=review_status, reviewed_by_user_id="usr_admin", decision_note="Review completed.",
        )
        await governance.emit(DomainEvent(
            event_type=EventType.RETENTION_CASE_DECIDED,
            actor="usr_admin",
            subject_type="candidate",
            subject_id=candidate.candidate_id,
            organization_id="org_alpha",
            payload={"retention_case_id": reviewed.retention_case_id, "decision": review_status.value},
            correlation_id=correlation_id,
        ))
        queued = await runtime.execute(ExecutionRecord(
            organization_id="org_alpha", user_id="usr_admin", user_role="admin",
            goal=f"Execute reviewed retention {requested_action}", correlation_id=correlation_id,
            steps=[PlanStep(
                capability_id=capability_id,
                inputs={"retention_case_id": retention_case.retention_case_id},
                sensitivity="restricted",
            )],
        ))
        assert queued.status == ExecutionStatus.AWAITING_APPROVAL
        assert world.executed_actions == []
        await governance.decide_approval(queued.pending_approvals[0], "granted", "usr_admin")
        completed = await runtime.resume_after_approval(queued.execution_id, "org_alpha")
        return retention_case, completed, await governance.replay(correlation_id)

    retention_case, completed, events = asyncio.run(run_lifecycle())

    assert completed.status == ExecutionStatus.SUCCEEDED
    assert retention_case.status == RetentionCaseStatus.COMPLETED
    assert world.executed_actions == [requested_action]
    if requested_action == "archive":
        assert candidate.archived_at is not None
    else:
        assert candidate.erased_at is not None
        assert candidate.full_name == "Redacted candidate"
        assert candidate.email is None
        assert candidate.skills == []
    assert {event.event_type for event in events} >= {
        EventType.RETENTION_CASE_REQUESTED,
        EventType.RETENTION_CASE_DECIDED,
        EventType.APPROVAL_REQUESTED,
        EventType.APPROVAL_GRANTED,
        EventType.EXECUTION_RESUMED,
        EventType.EXECUTION_COMPLETED,
    }
