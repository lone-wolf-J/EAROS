"""World State — single source of truth.

Contains Organizations, Departments, Teams, Requisitions (Jobs), Candidates,
Offers, Skills, Policies, Pipelines, and current execution state.

Planner always reasons AGAINST World State (never against LLM memory alone).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, ConfigDict, Field

from foundation import (
    ApplicationStatus,
    AuditExportStatus,
    ConsentStatus,
    DataSubjectRequestStatus,
    InterviewStatus,
    JobStatus,
    OnboardingHandoffStatus,
    OfferStatus,
    PipelineStage,
    RequisitionStatus,
    RetentionCaseStatus,
    Sensitivity,
    new_activity_id,
    new_application_id,
    new_application_reactivation_request_id,
    new_candidate_id,
    new_candidate_tag_id,
    new_candidate_notification_delivery_id,
    new_communication_id,
    new_communication_template_id,
    new_consent_id,
    new_data_subject_request_id,
    new_department_id,
    new_disposition_reason_id,
    new_feedback_id,
    new_interview_debrief_id,
    new_hiring_decision_id,
    new_interview_id,
    new_job_id,
    new_mention_id,
    new_notification_preference_id,
    new_recruiter_alert_id,
    new_offer_id,
    new_onboarding_handoff_id,
    new_organization_id,
    new_pipeline_id,
    new_pipeline_stage_id,
    new_requisition_id,
    new_resume_id,
    new_retention_case_id,
    new_scorecard_id,
    new_skill_id,
    new_talent_pool_id,
    new_team_id,
    new_audit_export_id,
    utcnow_iso,
)


# ---------- Documents ----------

class Organization(BaseModel):
    model_config = ConfigDict(extra="ignore")
    organization_id: str = Field(default_factory=new_organization_id)
    name: str
    domain: str
    industry: str
    headquarters: str
    hq_country: str
    total_headcount: int = 0
    active_reqs: int = 0
    created_at: str = Field(default_factory=utcnow_iso)


class Department(BaseModel):
    model_config = ConfigDict(extra="ignore")
    department_id: str = Field(default_factory=new_department_id)
    organization_id: str
    name: str
    leader_name: str
    headcount: int = 0
    attrition_rate: float = 0.0
    health_score: float = 0.75


class Team(BaseModel):
    model_config = ConfigDict(extra="ignore")
    team_id: str = Field(default_factory=new_team_id)
    department_id: str
    organization_id: str
    name: str
    manager_name: str
    headcount: int = 0
    open_seats: int = 0


class Skill(BaseModel):
    model_config = ConfigDict(extra="ignore")
    skill_id: str = Field(default_factory=new_skill_id)
    name: str
    category: str  # technical | functional | leadership | domain
    market_scarcity: float = 0.5  # 0..1 higher = scarcer


class Job(BaseModel):
    """Open requisition."""
    model_config = ConfigDict(extra="ignore")
    job_id: str = Field(default_factory=new_job_id)
    organization_id: str
    department_id: str
    team_id: Optional[str] = None
    title: str
    level: str  # IC3, IC4, IC5, M4, M5, VP
    location: str
    country: str  # India | USA
    employment_type: str = "Full-time"
    salary_min: int
    salary_max: int
    currency: str
    required_skills: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    priority: str = "P2"  # P0 P1 P2 P3
    business_impact: str
    status: JobStatus = JobStatus.OPEN
    hiring_manager: str
    opened_days_ago: int = 0
    target_close_days: int = 45
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    created_at: str = Field(default_factory=utcnow_iso)


class PipelineStageDefinition(BaseModel):
    """A tenant-configurable stage used by one or more recruiting pipelines."""
    model_config = ConfigDict(extra="ignore")
    stage_id: str = Field(default_factory=new_pipeline_stage_id)
    name: str
    category: str = "active"  # active | terminal_hired | terminal_rejected | terminal_withdrawn
    order: int = Field(ge=0)
    is_default: bool = False
    requires_feedback: bool = False
    requires_approval: bool = False


class Pipeline(BaseModel):
    """Reusable hiring process template; stage history belongs on applications."""
    model_config = ConfigDict(extra="ignore")
    pipeline_id: str = Field(default_factory=new_pipeline_id)
    organization_id: str
    name: str
    description: Optional[str] = None
    stages: list[PipelineStageDefinition] = Field(default_factory=list)
    is_default: bool = False
    archived_at: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)


class Requisition(BaseModel):
    """Approval-aware requisition and hiring-plan record, distinct from a published job."""
    model_config = ConfigDict(extra="ignore")
    requisition_id: str = Field(default_factory=new_requisition_id)
    organization_id: str
    job_id: Optional[str] = None
    title: str
    requisition_code: Optional[str] = None
    department_id: Optional[str] = None
    team_id: Optional[str] = None
    hiring_manager_id: Optional[str] = None
    recruiter_ids: list[str] = Field(default_factory=list)
    coordinator_ids: list[str] = Field(default_factory=list)
    headcount: int = Field(default=1, ge=1)
    headcount_type: str = "new"
    replacement_for: Optional[str] = None
    employment_type: str = "full_time"
    seniority: Optional[str] = None
    work_arrangement: str = "onsite"
    location: Optional[str] = None
    country: Optional[str] = None
    additional_locations: list[str] = Field(default_factory=list)
    cost_center: Optional[str] = None
    priority: str = "normal"
    compensation: dict[str, Any] = Field(default_factory=dict)
    internal_description: Optional[str] = None
    public_description: Optional[str] = None
    responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    evaluation_plan: dict[str, Any] = Field(default_factory=dict)
    stage_slas: dict[str, Any] = Field(default_factory=dict)
    offer_approval_route: list[str] = Field(default_factory=list)
    compliance: dict[str, Any] = Field(default_factory=dict)
    visibility: str = "internal"
    target_start_date: Optional[str] = None
    target_close_date: Optional[str] = None
    hiring_plan: dict[str, Any] = Field(default_factory=dict)
    approval_status: RequisitionStatus = RequisitionStatus.DRAFT
    pipeline_id: Optional[str] = None
    internal_publication_status: str = "draft"  # draft | published | closed
    external_publication_status: str = "not_requested"  # not_requested | draft_ready | pending_approval
    external_publication_targets: list[str] = Field(default_factory=list)
    career_site_enabled: bool = False
    referral_intake_enabled: bool = False
    application_questions: list[dict[str, Any]] = Field(default_factory=list)
    created_by_user_id: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)
    archived_at: Optional[str] = None


class NotificationPreference(BaseModel):
    """Per-user delivery choices. Provider delivery is never inferred from a preference."""
    model_config = ConfigDict(extra="ignore")
    notification_preference_id: str = Field(default_factory=new_notification_preference_id)
    organization_id: str
    user_id: str
    in_app_enabled: bool = True
    email_enabled: bool = False
    interview_reminders: bool = True
    approval_alerts: bool = True
    candidate_activity_alerts: bool = True
    provider_delivery_state: str = "not_configured"
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)


class CandidateNotificationDelivery(BaseModel):
    """Auditable candidate-notification intent. It never implies provider delivery."""
    model_config = ConfigDict(extra="ignore")
    candidate_notification_delivery_id: str = Field(default_factory=new_candidate_notification_delivery_id)
    organization_id: str
    candidate_id: str
    notification_type: str
    channel: str = "email"
    subject: Optional[str] = None
    body: Optional[str] = None
    delivery_state: str = "not_delivered"  # awaiting explicit provider configuration
    delivery_reason: str = "provider_not_configured"
    consent_id: Optional[str] = None
    created_by_user_id: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)


class RecruiterAlert(BaseModel):
    """Tenant-scoped in-app alert; recipients must be organization users."""
    model_config = ConfigDict(extra="ignore")
    recruiter_alert_id: str = Field(default_factory=new_recruiter_alert_id)
    organization_id: str
    recipient_user_id: str
    alert_type: str
    title: str
    body: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    status: str = "unread"
    created_by_user_id: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)
    read_at: Optional[str] = None


class Candidate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    candidate_id: str = Field(default_factory=new_candidate_id)
    organization_id: str
    job_id: Optional[str] = None
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: str = ""
    country: str = ""
    current_title: str = ""
    current_company: str = ""
    years_experience: float = 0.0
    expected_salary: int = 0
    currency: str = "USD"
    skills: list[str] = Field(default_factory=list)
    stage: PipelineStage = PipelineStage.SOURCED
    source: str = "sourced"  # sourced | applied | referral | agency
    source_detail: Optional[str] = None
    fit_score: float = 0.0  # populated by intelligence
    risk_flags: list[str] = Field(default_factory=list)
    picture: Optional[str] = None
    linkedin_url: Optional[str] = None
    external_profile_ids: dict[str, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    notes: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=utcnow_iso)
    archived_at: Optional[str] = None
    erased_at: Optional[str] = None
    retention_case_id: Optional[str] = None


class CandidateTag(BaseModel):
    """Reusable, organization-scoped candidate label administered by recruiting."""
    model_config = ConfigDict(extra="ignore")
    candidate_tag_id: str = Field(default_factory=new_candidate_tag_id)
    organization_id: str
    name: str
    normalized_name: str
    color: str = "slate"
    description: Optional[str] = None
    created_by_user_id: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)


class Application(BaseModel):
    """Candidate-to-requisition record with immutable stage movement history."""
    model_config = ConfigDict(extra="ignore")
    application_id: str = Field(default_factory=new_application_id)
    organization_id: str
    candidate_id: str
    requisition_id: Optional[str] = None
    job_id: Optional[str] = None
    pipeline_id: Optional[str] = None
    current_stage_id: Optional[str] = None
    current_stage_name: str = "Applied"
    status: ApplicationStatus = ApplicationStatus.ACTIVE
    source: str = "manual"
    source_detail: Optional[str] = None
    referral_user_id: Optional[str] = None
    fit_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    score_summary: Optional[str] = None
    skill_gaps: list[str] = Field(default_factory=list)
    application_answers: list[dict[str, Any]] = Field(default_factory=list)
    stage_history: list[dict[str, Any]] = Field(default_factory=list)
    withdrawal_token_hash: Optional[str] = None
    withdrawal_reason: Optional[str] = None
    withdrawn_at: Optional[str] = None
    applied_at: str = Field(default_factory=utcnow_iso)
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)
    archived_at: Optional[str] = None
    erased_at: Optional[str] = None
    retention_case_id: Optional[str] = None


class HiringDecision(BaseModel):
    """A recruiter-requested final outcome that is ineffective until independently approved."""
    model_config = ConfigDict(extra="ignore")
    hiring_decision_id: str = Field(default_factory=new_hiring_decision_id)
    organization_id: str
    application_id: str
    candidate_id: str
    requisition_id: Optional[str] = None
    outcome: str = Field(pattern="^(hire|reject)$")
    rationale: str = Field(min_length=10, max_length=10_000)
    disposition_reason_code: Optional[str] = None
    disposition_reason_label: Optional[str] = None
    requested_by_user_id: str
    approval_id: Optional[str] = None
    status: str = "awaiting_approval"  # awaiting_approval | effective | denied
    resolved_by_user_id: Optional[str] = None
    resolved_at: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)


class ApplicationReactivationRequest(BaseModel):
    """A governed correction that returns a terminal hire/reject application to an active stage.

    The originating hiring decision is never changed. A distinct independent approval
    must become effective before the application may be made active again.
    """
    model_config = ConfigDict(extra="ignore")
    application_reactivation_request_id: str = Field(default_factory=new_application_reactivation_request_id)
    organization_id: str
    application_id: str
    candidate_id: str
    requisition_id: Optional[str] = None
    terminal_status: str = Field(pattern="^(hired|rejected)$")
    target_stage_id: Optional[str] = None
    target_stage_name: str = Field(min_length=1, max_length=120)
    rationale: str = Field(min_length=10, max_length=10_000)
    requested_by_user_id: str
    approval_id: Optional[str] = None
    status: str = "awaiting_approval"  # awaiting_approval | effective | denied
    resolved_by_user_id: Optional[str] = None
    resolved_at: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)


class TalentPool(BaseModel):
    model_config = ConfigDict(extra="ignore")
    talent_pool_id: str = Field(default_factory=new_talent_pool_id)
    organization_id: str
    name: str
    description: Optional[str] = None
    owner_user_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utcnow_iso)
    archived_at: Optional[str] = None


class TalentPoolMembership(BaseModel):
    model_config = ConfigDict(extra="ignore")
    organization_id: str
    talent_pool_id: str
    candidate_id: str
    added_by_user_id: Optional[str] = None
    note: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)


class CandidateConsent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    consent_id: str = Field(default_factory=new_consent_id)
    organization_id: str
    candidate_id: str
    purpose: str  # recruiting | marketing | background_check | data_processing
    status: ConsentStatus = ConsentStatus.GRANTED
    legal_basis: Optional[str] = None
    captured_from: str = "manual"
    evidence_url: Optional[str] = None
    expires_at: Optional[str] = None
    recorded_by_user_id: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)


class ResumeDocument(BaseModel):
    model_config = ConfigDict(extra="ignore")
    resume_id: str = Field(default_factory=new_resume_id)
    organization_id: str
    candidate_id: str
    file_name: str
    storage_key: Optional[str] = None
    storage_url: Optional[str] = None
    mime_type: Optional[str] = None
    parse_status: str = "pending"  # pending | parsed | failed | manual
    parsed_profile: dict[str, Any] = Field(default_factory=dict)
    is_primary: bool = True
    uploaded_by_user_id: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)


class Interview(BaseModel):
    model_config = ConfigDict(extra="ignore")
    interview_id: str = Field(default_factory=new_interview_id)
    organization_id: str
    application_id: str
    candidate_id: str
    interview_type: str = "structured"
    stage_id: Optional[str] = None
    scheduled_at: str
    duration_minutes: int = Field(default=45, ge=15, le=480)
    timezone: str = "UTC"
    meeting_url: Optional[str] = None
    interviewer_ids: list[str] = Field(default_factory=list)
    status: InterviewStatus = InterviewStatus.SCHEDULED
    created_by_user_id: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)


class Scorecard(BaseModel):
    model_config = ConfigDict(extra="ignore")
    scorecard_id: str = Field(default_factory=new_scorecard_id)
    organization_id: str
    requisition_id: Optional[str] = None
    name: str
    competencies: list[dict[str, Any]] = Field(default_factory=list)
    created_by_user_id: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)


class InterviewFeedback(BaseModel):
    model_config = ConfigDict(extra="ignore")
    feedback_id: str = Field(default_factory=new_feedback_id)
    organization_id: str
    interview_id: str
    scorecard_id: Optional[str] = None
    interviewer_id: str
    recommendation: str  # strong_yes | yes | no | strong_no | abstain
    ratings: dict[str, float] = Field(default_factory=dict)
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    summary: Optional[str] = None
    submitted_at: str = Field(default_factory=utcnow_iso)


class InterviewDebrief(BaseModel):
    """Immutable, evidence-linked panel synthesis; it never changes application disposition or stage."""
    model_config = ConfigDict(extra="ignore")
    interview_debrief_id: str = Field(default_factory=new_interview_debrief_id)
    organization_id: str
    application_id: str
    candidate_id: str
    interview_ids: list[str] = Field(min_length=1, max_length=50)
    feedback_ids: list[str] = Field(min_length=1, max_length=500)
    participant_user_ids: list[str] = Field(default_factory=list, max_length=50)
    facilitator_user_id: str
    recommendation: str = "no_decision"  # advance | hold | decline | no_decision; never a final disposition
    evidence_summary: str = Field(min_length=10, max_length=20_000)
    unresolved_questions: list[str] = Field(default_factory=list, max_length=100)
    created_at: str = Field(default_factory=utcnow_iso)


class CollaborationMention(BaseModel):
    """A tenant-scoped recruiter or hiring-manager reference attached to a candidate record."""

    model_config = ConfigDict(extra="ignore")
    mention_id: str = Field(default_factory=new_mention_id)
    organization_id: str
    candidate_id: str
    mentioned_user_id: str
    mentioned_by_user_id: str
    feedback_id: Optional[str] = None
    context: Optional[str] = Field(default=None, max_length=2000)
    created_at: str = Field(default_factory=utcnow_iso)


class CandidateCommunication(BaseModel):
    """An immutable record of a human-operated candidate communication, never a delivery job."""

    model_config = ConfigDict(extra="ignore")
    communication_id: str = Field(default_factory=new_communication_id)
    organization_id: str
    candidate_id: str
    direction: str  # inbound | outbound
    channel: str  # email | phone | sms | in_app | other
    subject: Optional[str] = None
    body: Optional[str] = None
    delivery_state: str = "recorded"  # recorded only; delivery integrations are separate
    consent_id: Optional[str] = None
    recorded_by_user_id: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)


class DispositionReason(BaseModel):
    """Organization-owned outcome taxonomy; a code is stable for analytics and exports."""
    model_config = ConfigDict(extra="ignore")
    disposition_reason_id: str = Field(default_factory=new_disposition_reason_id)
    organization_id: str
    code: str
    label: str
    category: str = "rejected"
    is_active: bool = True
    created_by_user_id: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)


class CandidateCommunicationTemplate(BaseModel):
    """Reusable reviewed content. A template never implies an outbound provider send."""
    model_config = ConfigDict(extra="ignore")
    communication_template_id: str = Field(default_factory=new_communication_template_id)
    organization_id: str
    name: str
    channel: str
    subject: Optional[str] = None
    body: str
    stage_name: Optional[str] = None
    is_active: bool = True
    created_by_user_id: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)


class ActivityRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    activity_id: str = Field(default_factory=new_activity_id)
    organization_id: str
    entity_type: str
    entity_id: str
    event_type: str
    actor_user_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None
    occurred_at: str = Field(default_factory=utcnow_iso)


class RetentionCase(BaseModel):
    """A human-reviewed request to archive or erase a scoped recruiting record.

    The record captures a decision; it does not perform destructive data operations.
    """
    model_config = ConfigDict(extra="ignore")
    retention_case_id: str = Field(default_factory=new_retention_case_id)
    organization_id: str
    subject_type: str  # candidate | application | resume | talent_pool
    subject_id: str
    requested_action: str  # archive | erase
    reason: str
    requested_by_user_id: str
    legal_hold: bool = False
    status: RetentionCaseStatus = RetentionCaseStatus.PENDING_REVIEW
    reviewed_by_user_id: Optional[str] = None
    decision_note: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)
    completed_at: Optional[str] = None


class AuditExportManifest(BaseModel):
    """Auditable export request metadata; exported bytes remain outside the database."""
    model_config = ConfigDict(extra="ignore")
    audit_export_id: str = Field(default_factory=new_audit_export_id)
    organization_id: str
    requested_by_user_id: str
    filters: dict[str, Any] = Field(default_factory=dict)
    event_count: int = 0
    status: AuditExportStatus = AuditExportStatus.REQUESTED
    storage_key: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)


class DataSubjectRequest(BaseModel):
    """A human-reviewed access, correction, or erasure request for one candidate.

    The record itself never performs a destructive action. Erasure must progress
    through the separate policy-gated retention lifecycle before fulfillment.
    """
    model_config = ConfigDict(extra="ignore")
    data_subject_request_id: str = Field(default_factory=new_data_subject_request_id)
    organization_id: str
    candidate_id: str
    request_type: str  # access | correction | erasure
    request_summary: str
    intake_channel: str = "staff_recorded"
    requested_by_user_id: str
    status: DataSubjectRequestStatus = DataSubjectRequestStatus.PENDING_REVIEW
    reviewed_by_user_id: Optional[str] = None
    review_note: Optional[str] = None
    retention_case_id: Optional[str] = None
    audit_export_id: Optional[str] = None
    fulfilled_by_user_id: Optional[str] = None
    fulfilled_at: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)


class Offer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    offer_id: str = Field(default_factory=new_offer_id)
    organization_id: str
    candidate_id: str
    job_id: str
    base_salary: int
    bonus: int = 0
    equity_units: int = 0
    signing_bonus: int = 0
    currency: str
    status: OfferStatus = OfferStatus.DRAFT
    acceptance_probability: float = 0.0
    market_percentile: float = 0.0
    internal_parity_delta: float = 0.0
    reasoning_decision_id: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)


class OnboardingHandoff(BaseModel):
    """A minimal, auditable transfer record for an accepted hire.

    It carries routing and checklist metadata only. Identity-provider credentials,
    background-check documents, payroll details, and other sensitive onboarding
    payloads remain in their dedicated downstream systems.
    """
    model_config = ConfigDict(extra="ignore")
    onboarding_handoff_id: str = Field(default_factory=new_onboarding_handoff_id)
    organization_id: str
    offer_id: str
    candidate_id: str
    job_id: str
    application_id: Optional[str] = None
    target_start_date: Optional[str] = None
    owner_user_id: Optional[str] = None
    destination_system: Optional[str] = None
    checklist: list[dict[str, Any]] = Field(default_factory=list)
    status: OnboardingHandoffStatus = OnboardingHandoffStatus.DRAFT
    acknowledged_by_user_id: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)


# ---------- Repository ----------

class WorldState:
    """Repository facade over MongoDB. All queries exclude _id."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    # organization
    async def upsert_organization(self, org: Organization) -> Organization:
        await self.db.organizations.update_one(
            {"organization_id": org.organization_id}, {"$set": org.model_dump()}, upsert=True
        )
        return org

    async def get_organization(self, organization_id: str) -> Optional[Organization]:
        doc = await self.db.organizations.find_one({"organization_id": organization_id}, {"_id": 0})
        return Organization(**doc) if doc else None

    async def list_organizations(self) -> list[Organization]:
        docs = await self.db.organizations.find({}, {"_id": 0}).to_list(100)
        return [Organization(**d) for d in docs]

    # departments / teams
    async def upsert_department(self, d: Department) -> Department:
        await self.db.departments.update_one(
            {"department_id": d.department_id}, {"$set": d.model_dump()}, upsert=True
        )
        return d

    async def list_departments(self, organization_id: str) -> list[Department]:
        docs = await self.db.departments.find(
            {"organization_id": organization_id}, {"_id": 0}
        ).to_list(500)
        return [Department(**d) for d in docs]

    async def upsert_team(self, t: Team) -> Team:
        await self.db.teams.update_one(
            {"team_id": t.team_id}, {"$set": t.model_dump()}, upsert=True
        )
        return t

    async def list_teams(self, organization_id: str) -> list[Team]:
        docs = await self.db.teams.find(
            {"organization_id": organization_id}, {"_id": 0}
        ).to_list(500)
        return [Team(**d) for d in docs]

    # skills
    async def upsert_skill(self, s: Skill) -> Skill:
        await self.db.skills.update_one(
            {"skill_id": s.skill_id}, {"$set": s.model_dump()}, upsert=True
        )
        return s

    async def list_skills(self) -> list[Skill]:
        docs = await self.db.skills.find({}, {"_id": 0}).to_list(1000)
        return [Skill(**d) for d in docs]

    # jobs
    async def upsert_job(self, j: Job) -> Job:
        await self.db.jobs.update_one(
            {"job_id": j.job_id}, {"$set": j.model_dump()}, upsert=True
        )
        return j

    async def get_job(self, job_id: str) -> Optional[Job]:
        doc = await self.db.jobs.find_one({"job_id": job_id}, {"_id": 0})
        return Job(**doc) if doc else None

    async def get_job_for_organization(self, organization_id: str, job_id: str) -> Optional[Job]:
        """Resolve a job only when it belongs to the active tenant."""
        doc = await self.db.jobs.find_one(
            {"organization_id": organization_id, "job_id": job_id}, {"_id": 0}
        )
        return Job(**doc) if doc else None

    async def list_jobs(self, organization_id: str, status: Optional[JobStatus] = None) -> list[Job]:
        q: dict[str, Any] = {"organization_id": organization_id}
        if status:
            q["status"] = status.value
        docs = await self.db.jobs.find(q, {"_id": 0}).to_list(500)
        return [Job(**d) for d in docs]

    # reusable pipelines
    async def upsert_pipeline(self, pipeline: Pipeline) -> Pipeline:
        pipeline.updated_at = utcnow_iso()
        await self.db.pipelines.update_one(
            {"organization_id": pipeline.organization_id, "pipeline_id": pipeline.pipeline_id},
            {"$set": pipeline.model_dump()},
            upsert=True,
        )
        return pipeline

    async def get_pipeline(self, organization_id: str, pipeline_id: str) -> Optional[Pipeline]:
        doc = await self.db.pipelines.find_one(
            {"organization_id": organization_id, "pipeline_id": pipeline_id}, {"_id": 0}
        )
        return Pipeline(**doc) if doc else None

    async def list_pipelines(self, organization_id: str, include_archived: bool = False) -> list[Pipeline]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if not include_archived:
            query["archived_at"] = None
        docs = await self.db.pipelines.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
        return [Pipeline(**doc) for doc in docs]

    # requisitions and hiring plans
    async def upsert_requisition(self, requisition: Requisition) -> Requisition:
        requisition.updated_at = utcnow_iso()
        await self.db.requisitions.update_one(
            {"organization_id": requisition.organization_id, "requisition_id": requisition.requisition_id},
            {"$set": requisition.model_dump()},
            upsert=True,
        )
        return requisition

    async def get_requisition(self, organization_id: str, requisition_id: str) -> Optional[Requisition]:
        doc = await self.db.requisitions.find_one(
            {"organization_id": organization_id, "requisition_id": requisition_id}, {"_id": 0}
        )
        return Requisition(**doc) if doc else None

    async def list_requisitions(
        self, organization_id: str, status: Optional[RequisitionStatus] = None, include_archived: bool = False
    ) -> list[Requisition]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if status:
            query["approval_status"] = status.value
        if not include_archived:
            query["archived_at"] = None
        docs = await self.db.requisitions.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
        return [Requisition(**doc) for doc in docs]

    # personal notification delivery preferences
    async def get_notification_preference(self, organization_id: str, user_id: str) -> Optional[NotificationPreference]:
        doc = await self.db.notification_preferences.find_one(
            {"organization_id": organization_id, "user_id": user_id}, {"_id": 0}
        )
        return NotificationPreference(**doc) if doc else None

    async def upsert_notification_preference(self, preference: NotificationPreference) -> NotificationPreference:
        preference.updated_at = utcnow_iso()
        await self.db.notification_preferences.update_one(
            {"organization_id": preference.organization_id, "user_id": preference.user_id},
            {"$set": preference.model_dump()},
            upsert=True,
        )
        return preference

    async def record_candidate_notification_delivery(
        self, delivery: CandidateNotificationDelivery
    ) -> CandidateNotificationDelivery:
        await self.db.candidate_notification_deliveries.insert_one(delivery.model_dump())
        return delivery

    async def list_candidate_notification_deliveries(
        self, organization_id: str, candidate_id: str
    ) -> list[CandidateNotificationDelivery]:
        docs = await self.db.candidate_notification_deliveries.find(
            {"organization_id": organization_id, "candidate_id": candidate_id}, {"_id": 0}
        ).sort("created_at", -1).to_list(200)
        return [CandidateNotificationDelivery(**doc) for doc in docs]

    async def create_recruiter_alert(self, alert: RecruiterAlert) -> RecruiterAlert:
        await self.db.recruiter_alerts.insert_one(alert.model_dump())
        return alert

    async def list_recruiter_alerts(
        self, organization_id: str, recipient_user_id: str, unread_only: bool = False
    ) -> list[RecruiterAlert]:
        query: dict[str, Any] = {"organization_id": organization_id, "recipient_user_id": recipient_user_id}
        if unread_only:
            query["status"] = "unread"
        docs = await self.db.recruiter_alerts.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
        return [RecruiterAlert(**doc) for doc in docs]

    async def mark_recruiter_alert_read(
        self, organization_id: str, recipient_user_id: str, recruiter_alert_id: str
    ) -> Optional[RecruiterAlert]:
        await self.db.recruiter_alerts.update_one(
            {"organization_id": organization_id, "recipient_user_id": recipient_user_id, "recruiter_alert_id": recruiter_alert_id},
            {"$set": {"status": "read", "read_at": utcnow_iso()}},
        )
        doc = await self.db.recruiter_alerts.find_one(
            {"organization_id": organization_id, "recipient_user_id": recipient_user_id, "recruiter_alert_id": recruiter_alert_id}, {"_id": 0}
        )
        return RecruiterAlert(**doc) if doc else None

    # candidates
    async def upsert_candidate(self, c: Candidate) -> Candidate:
        await self.db.candidates.update_one(
            {"organization_id": c.organization_id, "candidate_id": c.candidate_id},
            {"$set": c.model_dump()},
            upsert=True,
        )
        return c

    async def get_candidate(self, candidate_id: str) -> Optional[Candidate]:
        doc = await self.db.candidates.find_one({"candidate_id": candidate_id}, {"_id": 0})
        return Candidate(**doc) if doc else None

    async def get_candidate_for_organization(
        self, organization_id: str, candidate_id: str
    ) -> Optional[Candidate]:
        """Resolve a candidate only when it belongs to the active tenant."""
        doc = await self.db.candidates.find_one(
            {"organization_id": organization_id, "candidate_id": candidate_id}, {"_id": 0}
        )
        return Candidate(**doc) if doc else None

    async def list_candidates(
        self,
        organization_id: str,
        job_id: Optional[str] = None,
        stage: Optional[PipelineStage] = None,
        include_archived: bool = False,
    ) -> list[Candidate]:
        q: dict[str, Any] = {"organization_id": organization_id}
        if job_id:
            q["job_id"] = job_id
        if stage:
            q["stage"] = stage.value
        if not include_archived:
            q["archived_at"] = None
        docs = await self.db.candidates.find(q, {"_id": 0}).to_list(2000)
        return [Candidate(**d) for d in docs]

    async def search_candidates(
        self,
        organization_id: str,
        *,
        query: Optional[str] = None,
        tags: Optional[list[str]] = None,
        source: Optional[str] = None,
        minimum_fit_score: Optional[float] = None,
    ) -> list[Candidate]:
        """Search active tenant candidates using bounded in-process matching for portability."""
        candidates = await self.list_candidates(organization_id)
        terms = [term.strip().lower() for term in (query or "").split() if term.strip()]
        requested_tags = {tag.strip().lower() for tag in (tags or []) if tag.strip()}
        source_value = (source or "").strip().lower()
        result: list[Candidate] = []
        for candidate in candidates:
            haystack = " ".join([
                candidate.full_name,
                candidate.email or "",
                candidate.location,
                candidate.current_title,
                candidate.current_company,
                candidate.source,
                candidate.source_detail or "",
                " ".join(candidate.skills),
                " ".join(candidate.tags),
            ]).lower()
            if terms and not all(term in haystack for term in terms):
                continue
            candidate_tags = {tag.lower() for tag in candidate.tags}
            if requested_tags and not requested_tags.issubset(candidate_tags):
                continue
            if source_value and candidate.source.lower() != source_value:
                continue
            if minimum_fit_score is not None and candidate.fit_score < minimum_fit_score:
                continue
            result.append(candidate)
        return result

    async def upsert_candidate_tag(self, tag: CandidateTag) -> CandidateTag:
        await self.db.candidate_tags.update_one(
            {"organization_id": tag.organization_id, "normalized_name": tag.normalized_name},
            {"$set": tag.model_dump()},
            upsert=True,
        )
        return tag

    async def list_candidate_tags(self, organization_id: str) -> list[CandidateTag]:
        docs = await self.db.candidate_tags.find(
            {"organization_id": organization_id}, {"_id": 0}
        ).sort("name", 1).to_list(1000)
        return [CandidateTag(**doc) for doc in docs]

    async def update_candidate_crm(
        self,
        organization_id: str,
        candidate_id: str,
        *,
        tags: Optional[list[str]] = None,
        source: Optional[str] = None,
        source_detail: Optional[str] = None,
        archived_at: Optional[str] = None,
    ) -> Optional[Candidate]:
        updates: dict[str, Any] = {}
        if tags is not None:
            updates["tags"] = list(dict.fromkeys(tag.strip() for tag in tags if tag.strip()))
        if source is not None:
            updates["source"] = source
        if source_detail is not None:
            updates["source_detail"] = source_detail
        if archived_at is not None:
            updates["archived_at"] = archived_at
        if not updates:
            return await self.get_candidate_for_organization(organization_id, candidate_id)
        await self.db.candidates.update_one(
            {"organization_id": organization_id, "candidate_id": candidate_id}, {"$set": updates}
        )
        return await self.get_candidate_for_organization(organization_id, candidate_id)

    async def set_candidate_stage(self, candidate_id: str, stage: PipelineStage) -> None:
        await self.db.candidates.update_one(
            {"candidate_id": candidate_id}, {"$set": {"stage": stage.value}}
        )

    async def set_candidate_stage_for_organization(
        self, organization_id: str, candidate_id: str, stage: PipelineStage
    ) -> bool:
        result = await self.db.candidates.update_one(
            {"organization_id": organization_id, "candidate_id": candidate_id},
            {"$set": {"stage": stage.value}},
        )
        return result.matched_count == 1

    async def add_candidate_note(self, candidate_id: str, note: dict[str, Any]) -> None:
        await self.db.candidates.update_one(
            {"candidate_id": candidate_id}, {"$push": {"notes": note}}
        )

    async def find_duplicate_candidate(
        self,
        organization_id: str,
        *,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        linkedin_url: Optional[str] = None,
    ) -> Optional[Candidate]:
        """Match only within a tenant; exact normalized identities prevent accidental duplicate profiles."""
        normalized_email = (email or "").strip().lower()
        normalized_phone = "".join(ch for ch in (phone or "") if ch.isdigit())
        normalized_linkedin = (linkedin_url or "").strip().rstrip("/").lower()
        if not any((normalized_email, normalized_phone, normalized_linkedin)):
            return None

        docs = await self.db.candidates.find({"organization_id": organization_id}, {"_id": 0}).to_list(5000)
        for doc in docs:
            candidate = Candidate(**doc)
            candidate_email = (candidate.email or "").strip().lower()
            candidate_phone = "".join(ch for ch in (candidate.phone or "") if ch.isdigit())
            candidate_linkedin = (candidate.linkedin_url or "").strip().rstrip("/").lower()
            if (
                normalized_email and candidate_email == normalized_email
            ) or (
                normalized_phone and candidate_phone == normalized_phone
            ) or (
                normalized_linkedin and candidate_linkedin == normalized_linkedin
            ):
                return candidate
        return None

    # candidate-to-job relationships
    async def upsert_application(self, application: Application) -> Application:
        application.updated_at = utcnow_iso()
        await self.db.applications.update_one(
            {"organization_id": application.organization_id, "application_id": application.application_id},
            {"$set": application.model_dump()},
            upsert=True,
        )
        return application

    async def get_application(self, organization_id: str, application_id: str) -> Optional[Application]:
        doc = await self.db.applications.find_one(
            {"organization_id": organization_id, "application_id": application_id}, {"_id": 0}
        )
        return Application(**doc) if doc else None

    async def get_application_by_id(self, application_id: str) -> Optional[Application]:
        """Lookup is reserved for public token validation; callers must not expose the result before verification."""
        doc = await self.db.applications.find_one({"application_id": application_id}, {"_id": 0})
        return Application(**doc) if doc else None

    async def list_applications(
        self,
        organization_id: str,
        *,
        candidate_id: Optional[str] = None,
        requisition_id: Optional[str] = None,
        status: Optional[ApplicationStatus] = None,
        include_archived: bool = False,
    ) -> list[Application]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if candidate_id:
            query["candidate_id"] = candidate_id
        if requisition_id:
            query["requisition_id"] = requisition_id
        if status:
            query["status"] = status.value
        if not include_archived:
            query["archived_at"] = None
        docs = await self.db.applications.find(query, {"_id": 0}).sort("created_at", -1).to_list(5000)
        return [Application(**doc) for doc in docs]

    async def upsert_disposition_reason(self, reason: DispositionReason) -> DispositionReason:
        reason.updated_at = utcnow_iso()
        await self.db.disposition_reasons.update_one(
            {"organization_id": reason.organization_id, "code": reason.code},
            {"$set": reason.model_dump()}, upsert=True,
        )
        return reason

    async def get_disposition_reason(self, organization_id: str, code: str) -> Optional[DispositionReason]:
        doc = await self.db.disposition_reasons.find_one(
            {"organization_id": organization_id, "code": code}, {"_id": 0}
        )
        return DispositionReason(**doc) if doc else None

    async def list_disposition_reasons(self, organization_id: str, *, active_only: bool = True) -> list[DispositionReason]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if active_only:
            query["is_active"] = True
        docs = await self.db.disposition_reasons.find(query, {"_id": 0}).sort("label", 1).to_list(500)
        return [DispositionReason(**doc) for doc in docs]

    # organization-owned disposition taxonomy
    async def upsert_disposition_reason(self, reason: DispositionReason) -> DispositionReason:
        reason.updated_at = utcnow_iso()
        await self.db.disposition_reasons.update_one(
            {"organization_id": reason.organization_id, "code": reason.code},
            {"$set": reason.model_dump()}, upsert=True,
        )
        return reason

    async def get_disposition_reason(self, organization_id: str, code: str) -> Optional[DispositionReason]:
        doc = await self.db.disposition_reasons.find_one(
            {"organization_id": organization_id, "code": code}, {"_id": 0}
        )
        return DispositionReason(**doc) if doc else None

    async def list_disposition_reasons(self, organization_id: str, *, active_only: bool = True) -> list[DispositionReason]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if active_only:
            query["is_active"] = True
        docs = await self.db.disposition_reasons.find(query, {"_id": 0}).sort("label", 1).to_list(500)
        return [DispositionReason(**doc) for doc in docs]

    # final hiring outcomes — a decision becomes effective only from the approval route
    async def create_hiring_decision(self, decision: HiringDecision) -> HiringDecision:
        await self.db.hiring_decisions.insert_one(decision.model_dump())
        return decision

    async def get_hiring_decision(self, organization_id: str, hiring_decision_id: str) -> Optional[HiringDecision]:
        doc = await self.db.hiring_decisions.find_one(
            {"organization_id": organization_id, "hiring_decision_id": hiring_decision_id}, {"_id": 0}
        )
        return HiringDecision(**doc) if doc else None

    async def list_hiring_decisions(
        self, organization_id: str, *, application_id: Optional[str] = None, candidate_id: Optional[str] = None
    ) -> list[HiringDecision]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if application_id:
            query["application_id"] = application_id
        if candidate_id:
            query["candidate_id"] = candidate_id
        docs = await self.db.hiring_decisions.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
        return [HiringDecision(**doc) for doc in docs]

    async def resolve_hiring_decision(
        self,
        organization_id: str,
        hiring_decision_id: str,
        *,
        approval_id: str,
        status: str,
        resolved_by_user_id: str,
    ) -> Optional[HiringDecision]:
        now = utcnow_iso()
        result = await self.db.hiring_decisions.update_one(
            {
                "organization_id": organization_id,
                "hiring_decision_id": hiring_decision_id,
                "approval_id": approval_id,
                "status": "awaiting_approval",
            },
            {"$set": {"status": status, "resolved_by_user_id": resolved_by_user_id, "resolved_at": now, "updated_at": now}},
        )
        if result.matched_count != 1:
            return await self.get_hiring_decision(organization_id, hiring_decision_id)
        return await self.get_hiring_decision(organization_id, hiring_decision_id)

    async def apply_hiring_decision_application_status(
        self, organization_id: str, decision: HiringDecision
    ) -> Optional[Application]:
        status = ApplicationStatus.HIRED if decision.outcome == "hire" else ApplicationStatus.REJECTED
        terminal_stage_name = "Hired" if decision.outcome == "hire" else "Rejected"
        now = utcnow_iso()
        result = await self.db.applications.update_one(
            {"organization_id": organization_id, "application_id": decision.application_id, "status": ApplicationStatus.ACTIVE.value},
            {"$set": {"status": status.value, "current_stage_id": None, "current_stage_name": terminal_stage_name, "updated_at": now}, "$push": {"stage_history": {"stage_name": terminal_stage_name, "changed_at": now, "reason": "approved_hiring_decision", "hiring_decision_id": decision.hiring_decision_id}}},
        )
        if result.matched_count != 1:
            return None
        return await self.get_application(organization_id, decision.application_id)

    # governed terminal application corrections; source hiring decisions remain immutable
    async def create_application_reactivation_request(
        self, request: ApplicationReactivationRequest
    ) -> ApplicationReactivationRequest:
        await self.db.application_reactivation_requests.insert_one(request.model_dump())
        return request

    async def get_application_reactivation_request(
        self, organization_id: str, application_reactivation_request_id: str
    ) -> Optional[ApplicationReactivationRequest]:
        doc = await self.db.application_reactivation_requests.find_one(
            {
                "organization_id": organization_id,
                "application_reactivation_request_id": application_reactivation_request_id,
            },
            {"_id": 0},
        )
        return ApplicationReactivationRequest(**doc) if doc else None

    async def list_application_reactivation_requests(
        self,
        organization_id: str,
        *,
        application_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[ApplicationReactivationRequest]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if application_id:
            query["application_id"] = application_id
        if status:
            query["status"] = status
        docs = await self.db.application_reactivation_requests.find(
            query, {"_id": 0}
        ).sort("created_at", -1).to_list(1000)
        return [ApplicationReactivationRequest(**doc) for doc in docs]

    async def resolve_application_reactivation_request(
        self,
        organization_id: str,
        application_reactivation_request_id: str,
        *,
        approval_id: str,
        status: str,
        resolved_by_user_id: str,
    ) -> Optional[ApplicationReactivationRequest]:
        now = utcnow_iso()
        result = await self.db.application_reactivation_requests.update_one(
            {
                "organization_id": organization_id,
                "application_reactivation_request_id": application_reactivation_request_id,
                "approval_id": approval_id,
                "status": "awaiting_approval",
            },
            {
                "$set": {
                    "status": status,
                    "resolved_by_user_id": resolved_by_user_id,
                    "resolved_at": now,
                    "updated_at": now,
                }
            },
        )
        if result.matched_count != 1:
            return await self.get_application_reactivation_request(
                organization_id, application_reactivation_request_id
            )
        return await self.get_application_reactivation_request(
            organization_id, application_reactivation_request_id
        )

    async def apply_application_reactivation(
        self,
        organization_id: str,
        request: ApplicationReactivationRequest,
        *,
        approval_id: str,
        resolved_by_user_id: str,
    ) -> Optional[Application]:
        """Make only the still-terminal target active and append durable correction provenance."""
        now = utcnow_iso()
        result = await self.db.applications.update_one(
            {
                "organization_id": organization_id,
                "application_id": request.application_id,
                "status": request.terminal_status,
            },
            {
                "$set": {
                    "status": ApplicationStatus.ACTIVE.value,
                    "current_stage_id": request.target_stage_id,
                    "current_stage_name": request.target_stage_name,
                    "updated_at": now,
                },
                "$push": {
                    "stage_history": {
                        "stage_id": request.target_stage_id,
                        "stage_name": request.target_stage_name,
                        "changed_at": now,
                        "actor_user_id": resolved_by_user_id,
                        "reason": "approved_application_reactivation",
                        "application_reactivation_request_id": request.application_reactivation_request_id,
                        "approval_id": approval_id,
                        "from_terminal_status": request.terminal_status,
                    }
                },
            },
        )
        if result.matched_count != 1:
            return None
        return await self.get_application(organization_id, request.application_id)

    # candidate relationship management
    async def upsert_talent_pool(self, pool: TalentPool) -> TalentPool:
        await self.db.talent_pools.update_one(
            {"organization_id": pool.organization_id, "talent_pool_id": pool.talent_pool_id},
            {"$set": pool.model_dump()},
            upsert=True,
        )
        return pool

    async def list_talent_pools(self, organization_id: str, include_archived: bool = False) -> list[TalentPool]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if not include_archived:
            query["archived_at"] = None
        docs = await self.db.talent_pools.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
        return [TalentPool(**doc) for doc in docs]

    async def add_to_talent_pool(self, membership: TalentPoolMembership) -> TalentPoolMembership:
        await self.db.talent_pool_memberships.update_one(
            {
                "organization_id": membership.organization_id,
                "talent_pool_id": membership.talent_pool_id,
                "candidate_id": membership.candidate_id,
            },
            {"$setOnInsert": membership.model_dump()},
            upsert=True,
        )
        return membership

    async def list_talent_pool_members(
        self, organization_id: str, talent_pool_id: str
    ) -> list[TalentPoolMembership]:
        docs = await self.db.talent_pool_memberships.find(
            {"organization_id": organization_id, "talent_pool_id": talent_pool_id}, {"_id": 0}
        ).sort("created_at", -1).to_list(5000)
        return [TalentPoolMembership(**doc) for doc in docs]

    # consent and resume lifecycle
    async def upsert_consent(self, consent: CandidateConsent) -> CandidateConsent:
        consent.updated_at = utcnow_iso()
        await self.db.candidate_consents.update_one(
            {"organization_id": consent.organization_id, "consent_id": consent.consent_id},
            {"$set": consent.model_dump()},
            upsert=True,
        )
        return consent

    async def list_candidate_consents(self, organization_id: str, candidate_id: str) -> list[CandidateConsent]:
        docs = await self.db.candidate_consents.find(
            {"organization_id": organization_id, "candidate_id": candidate_id}, {"_id": 0}
        ).sort("created_at", -1).to_list(200)
        return [CandidateConsent(**doc) for doc in docs]

    async def upsert_resume(self, resume: ResumeDocument) -> ResumeDocument:
        resume.updated_at = utcnow_iso()
        if resume.is_primary:
            await self.db.resumes.update_many(
                {"organization_id": resume.organization_id, "candidate_id": resume.candidate_id},
                {"$set": {"is_primary": False, "updated_at": resume.updated_at}},
            )
        await self.db.resumes.update_one(
            {"organization_id": resume.organization_id, "resume_id": resume.resume_id},
            {"$set": resume.model_dump()},
            upsert=True,
        )
        return resume

    async def list_resumes(self, organization_id: str, candidate_id: str) -> list[ResumeDocument]:
        docs = await self.db.resumes.find(
            {"organization_id": organization_id, "candidate_id": candidate_id}, {"_id": 0}
        ).sort("created_at", -1).to_list(100)
        return [ResumeDocument(**doc) for doc in docs]

    # structured interviewing and feedback
    async def upsert_interview(self, interview: Interview) -> Interview:
        interview.updated_at = utcnow_iso()
        await self.db.interviews.update_one(
            {"organization_id": interview.organization_id, "interview_id": interview.interview_id},
            {"$set": interview.model_dump()},
            upsert=True,
        )
        return interview

    async def get_interview(self, organization_id: str, interview_id: str) -> Optional[Interview]:
        doc = await self.db.interviews.find_one(
            {"organization_id": organization_id, "interview_id": interview_id}, {"_id": 0}
        )
        return Interview(**doc) if doc else None

    async def list_interviews(
        self,
        organization_id: str,
        *,
        application_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        status: Optional[InterviewStatus] = None,
    ) -> list[Interview]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if application_id:
            query["application_id"] = application_id
        if candidate_id:
            query["candidate_id"] = candidate_id
        if status:
            query["status"] = status.value
        docs = await self.db.interviews.find(query, {"_id": 0}).sort("scheduled_at", 1).to_list(5000)
        return [Interview(**doc) for doc in docs]

    async def upsert_scorecard(self, scorecard: Scorecard) -> Scorecard:
        scorecard.updated_at = utcnow_iso()
        await self.db.scorecards.update_one(
            {"organization_id": scorecard.organization_id, "scorecard_id": scorecard.scorecard_id},
            {"$set": scorecard.model_dump()},
            upsert=True,
        )
        return scorecard

    async def get_scorecard(self, organization_id: str, scorecard_id: str) -> Optional[Scorecard]:
        doc = await self.db.scorecards.find_one(
            {"organization_id": organization_id, "scorecard_id": scorecard_id}, {"_id": 0}
        )
        return Scorecard(**doc) if doc else None

    async def list_scorecards(self, organization_id: str, requisition_id: Optional[str] = None) -> list[Scorecard]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if requisition_id:
            query["requisition_id"] = requisition_id
        docs = await self.db.scorecards.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
        return [Scorecard(**doc) for doc in docs]

    async def upsert_interview_feedback(self, feedback: InterviewFeedback) -> InterviewFeedback:
        await self.db.interview_feedback.update_one(
            {"organization_id": feedback.organization_id, "feedback_id": feedback.feedback_id},
            {"$set": feedback.model_dump()},
            upsert=True,
        )
        return feedback

    async def get_interview_feedback(self, organization_id: str, feedback_id: str) -> Optional[InterviewFeedback]:
        doc = await self.db.interview_feedback.find_one(
            {"organization_id": organization_id, "feedback_id": feedback_id}, {"_id": 0}
        )
        return InterviewFeedback(**doc) if doc else None

    async def list_interview_feedback(self, organization_id: str, interview_id: str) -> list[InterviewFeedback]:
        docs = await self.db.interview_feedback.find(
            {"organization_id": organization_id, "interview_id": interview_id}, {"_id": 0}
        ).sort("submitted_at", -1).to_list(1000)
        return [InterviewFeedback(**doc) for doc in docs]

    async def record_interview_debrief(self, debrief: InterviewDebrief) -> InterviewDebrief:
        await self.db.interview_debriefs.insert_one(debrief.model_dump())
        return debrief

    async def list_interview_debriefs(self, organization_id: str, application_id: str) -> list[InterviewDebrief]:
        docs = await self.db.interview_debriefs.find(
            {"organization_id": organization_id, "application_id": application_id}, {"_id": 0}
        ).sort("created_at", -1).to_list(500)
        return [InterviewDebrief(**doc) for doc in docs]

    async def record_collaboration_mention(self, mention: CollaborationMention) -> CollaborationMention:
        await self.db.collaboration_mentions.insert_one(mention.model_dump())
        return mention

    async def list_collaboration_mentions(
        self, organization_id: str, candidate_id: str, limit: int = 100
    ) -> list[CollaborationMention]:
        docs = await self.db.collaboration_mentions.find(
            {"organization_id": organization_id, "candidate_id": candidate_id}, {"_id": 0}
        ).sort("created_at", -1).to_list(min(max(limit, 1), 500))
        return [CollaborationMention(**doc) for doc in docs]

    async def record_candidate_communication(self, communication: CandidateCommunication) -> CandidateCommunication:
        await self.db.candidate_communications.insert_one(communication.model_dump())
        return communication

    async def list_candidate_communications(
        self, organization_id: str, candidate_id: str, limit: int = 100
    ) -> list[CandidateCommunication]:
        docs = await self.db.candidate_communications.find(
            {"organization_id": organization_id, "candidate_id": candidate_id}, {"_id": 0}
        ).sort("created_at", -1).to_list(min(max(limit, 1), 500))
        return [CandidateCommunication(**doc) for doc in docs]

    # append-only operational history, separate from the governance event stream
    async def record_activity(self, activity: ActivityRecord) -> ActivityRecord:
        await self.db.activity_records.insert_one(activity.model_dump())
        return activity

    async def list_activity(
        self, organization_id: str, entity_type: str, entity_id: str, limit: int = 100
    ) -> list[ActivityRecord]:
        docs = await self.db.activity_records.find(
            {"organization_id": organization_id, "entity_type": entity_type, "entity_id": entity_id},
            {"_id": 0},
        ).sort("occurred_at", -1).to_list(min(max(limit, 1), 500))
        return [ActivityRecord(**doc) for doc in docs]

    # compliance review records — persistence only; destructive actions are never implicit
    async def create_retention_case(self, retention_case: RetentionCase) -> RetentionCase:
        await self.db.retention_cases.update_one(
            {
                "organization_id": retention_case.organization_id,
                "retention_case_id": retention_case.retention_case_id,
            },
            {"$set": retention_case.model_dump()},
            upsert=True,
        )
        return retention_case

    async def get_retention_case(
        self, organization_id: str, retention_case_id: str
    ) -> Optional[RetentionCase]:
        doc = await self.db.retention_cases.find_one(
            {"organization_id": organization_id, "retention_case_id": retention_case_id}, {"_id": 0}
        )
        return RetentionCase(**doc) if doc else None

    async def list_retention_cases(
        self, organization_id: str, status: Optional[RetentionCaseStatus] = None
    ) -> list[RetentionCase]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if status:
            query["status"] = status.value
        docs = await self.db.retention_cases.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
        return [RetentionCase(**doc) for doc in docs]

    async def decide_retention_case(
        self,
        organization_id: str,
        retention_case_id: str,
        *,
        status: RetentionCaseStatus,
        reviewed_by_user_id: str,
        decision_note: Optional[str] = None,
    ) -> Optional[RetentionCase]:
        if status not in {
            RetentionCaseStatus.ON_HOLD,
            RetentionCaseStatus.APPROVED_FOR_ARCHIVE,
            RetentionCaseStatus.APPROVED_FOR_ERASURE,
            RetentionCaseStatus.REJECTED,
        }:
            raise ValueError("retention decision must be a review outcome")
        now = utcnow_iso()
        result = await self.db.retention_cases.update_one(
            {"organization_id": organization_id, "retention_case_id": retention_case_id},
            {"$set": {
                "status": status.value,
                "reviewed_by_user_id": reviewed_by_user_id,
                "decision_note": decision_note,
                "updated_at": now,
            }},
        )
        if result.matched_count != 1:
            return None
        return await self.get_retention_case(organization_id, retention_case_id)

    async def execute_retention_case(
        self, organization_id: str, retention_case_id: str, *, expected_action: str
    ) -> Optional[RetentionCase]:
        """Apply one approved, non-held retention action without crossing tenant boundaries.

        Archive hides operational records. Erasure irreversibly redacts direct profile and
        application-evaluation data while retaining the minimum immutable identifiers needed
        to demonstrate that the governed action occurred.
        """
        retention_case = await self.get_retention_case(organization_id, retention_case_id)
        if not retention_case:
            return None
        if retention_case.status == RetentionCaseStatus.COMPLETED:
            return retention_case
        if retention_case.legal_hold:
            raise ValueError("retention case is on legal hold")
        expected_status = (
            RetentionCaseStatus.APPROVED_FOR_ARCHIVE
            if expected_action == "archive"
            else RetentionCaseStatus.APPROVED_FOR_ERASURE
        )
        if retention_case.requested_action != expected_action or retention_case.status != expected_status:
            raise ValueError("retention case does not have the required approved decision")

        now = utcnow_iso()
        if retention_case.subject_type == "candidate":
            selector = {"organization_id": organization_id, "candidate_id": retention_case.subject_id}
            if expected_action == "archive":
                update = {"archived_at": now, "retention_case_id": retention_case.retention_case_id}
            else:
                update = {
                    "full_name": "Erased candidate",
                    "email": None,
                    "phone": None,
                    "location": "",
                    "country": "",
                    "current_title": "",
                    "current_company": "",
                    "skills": [],
                    "picture": None,
                    "linkedin_url": None,
                    "external_profile_ids": {},
                    "tags": [],
                    "notes": [],
                    "archived_at": now,
                    "erased_at": now,
                    "retention_case_id": retention_case.retention_case_id,
                }
            result = await self.db.candidates.update_one(selector, {"$set": update})
        elif retention_case.subject_type == "application":
            selector = {"organization_id": organization_id, "application_id": retention_case.subject_id}
            update = {"archived_at": now, "retention_case_id": retention_case.retention_case_id}
            if expected_action == "erase":
                update.update({
                    "fit_score": None,
                    "score_summary": None,
                    "skill_gaps": [],
                    "stage_history": [],
                    "source_detail": None,
                    "erased_at": now,
                })
            result = await self.db.applications.update_one(selector, {"$set": update})
        else:
            raise ValueError("unsupported retention subject type")
        if result.matched_count != 1:
            return None

        await self.db.retention_cases.update_one(
            {"organization_id": organization_id, "retention_case_id": retention_case_id},
            {"$set": {
                "status": RetentionCaseStatus.COMPLETED.value,
                "completed_at": now,
                "updated_at": now,
            }},
        )
        return await self.get_retention_case(organization_id, retention_case_id)

    async def create_audit_export_manifest(self, manifest: AuditExportManifest) -> AuditExportManifest:
        await self.db.audit_export_manifests.update_one(
            {"organization_id": manifest.organization_id, "audit_export_id": manifest.audit_export_id},
            {"$set": manifest.model_dump()},
            upsert=True,
        )
        return manifest

    async def list_audit_export_manifests(self, organization_id: str) -> list[AuditExportManifest]:
        docs = await self.db.audit_export_manifests.find(
            {"organization_id": organization_id}, {"_id": 0}
        ).sort("created_at", -1).to_list(1000)
        return [AuditExportManifest(**doc) for doc in docs]

    async def create_data_subject_request(self, request: DataSubjectRequest) -> DataSubjectRequest:
        await self.db.data_subject_requests.update_one(
            {"organization_id": request.organization_id, "data_subject_request_id": request.data_subject_request_id},
            {"$set": request.model_dump()},
            upsert=True,
        )
        return request

    async def get_data_subject_request(
        self, organization_id: str, data_subject_request_id: str
    ) -> Optional[DataSubjectRequest]:
        doc = await self.db.data_subject_requests.find_one(
            {"organization_id": organization_id, "data_subject_request_id": data_subject_request_id}, {"_id": 0}
        )
        return DataSubjectRequest(**doc) if doc else None

    async def list_data_subject_requests(
        self, organization_id: str, status: Optional[DataSubjectRequestStatus] = None
    ) -> list[DataSubjectRequest]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if status:
            query["status"] = status.value
        docs = await self.db.data_subject_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
        return [DataSubjectRequest(**doc) for doc in docs]

    async def decide_data_subject_request(
        self,
        organization_id: str,
        data_subject_request_id: str,
        *,
        status: DataSubjectRequestStatus,
        reviewed_by_user_id: str,
        review_note: Optional[str] = None,
    ) -> Optional[DataSubjectRequest]:
        if status not in {DataSubjectRequestStatus.ON_HOLD, DataSubjectRequestStatus.APPROVED, DataSubjectRequestStatus.REJECTED}:
            raise ValueError("data-subject decision must be a review outcome")
        now = utcnow_iso()
        result = await self.db.data_subject_requests.update_one(
            {
                "organization_id": organization_id,
                "data_subject_request_id": data_subject_request_id,
                "status": DataSubjectRequestStatus.PENDING_REVIEW.value,
            },
            {"$set": {
                "status": status.value,
                "reviewed_by_user_id": reviewed_by_user_id,
                "review_note": review_note,
                "updated_at": now,
            }},
        )
        if result.matched_count != 1:
            return None
        return await self.get_data_subject_request(organization_id, data_subject_request_id)

    async def link_data_subject_request_artifact(
        self,
        organization_id: str,
        data_subject_request_id: str,
        *,
        retention_case_id: Optional[str] = None,
        audit_export_id: Optional[str] = None,
    ) -> Optional[DataSubjectRequest]:
        update: dict[str, Any] = {"updated_at": utcnow_iso()}
        if retention_case_id:
            update["retention_case_id"] = retention_case_id
        if audit_export_id:
            update["audit_export_id"] = audit_export_id
        result = await self.db.data_subject_requests.update_one(
            {"organization_id": organization_id, "data_subject_request_id": data_subject_request_id},
            {"$set": update},
        )
        if result.matched_count != 1:
            return None
        return await self.get_data_subject_request(organization_id, data_subject_request_id)

    async def fulfill_data_subject_request(
        self, organization_id: str, data_subject_request_id: str, *, fulfilled_by_user_id: str
    ) -> Optional[DataSubjectRequest]:
        now = utcnow_iso()
        result = await self.db.data_subject_requests.update_one(
            {
                "organization_id": organization_id,
                "data_subject_request_id": data_subject_request_id,
                "status": DataSubjectRequestStatus.APPROVED.value,
            },
            {"$set": {
                "status": DataSubjectRequestStatus.FULFILLED.value,
                "fulfilled_by_user_id": fulfilled_by_user_id,
                "fulfilled_at": now,
                "updated_at": now,
            }},
        )
        if result.matched_count != 1:
            return None
        return await self.get_data_subject_request(organization_id, data_subject_request_id)

    # onboarding handoff records — durable transfer metadata, never sensitive employee data
    async def upsert_onboarding_handoff(self, handoff: OnboardingHandoff) -> OnboardingHandoff:
        handoff.updated_at = utcnow_iso()
        await self.db.onboarding_handoffs.update_one(
            {
                "organization_id": handoff.organization_id,
                "onboarding_handoff_id": handoff.onboarding_handoff_id,
            },
            {"$set": handoff.model_dump()},
            upsert=True,
        )
        return handoff

    async def get_onboarding_handoff(
        self, organization_id: str, onboarding_handoff_id: str
    ) -> Optional[OnboardingHandoff]:
        doc = await self.db.onboarding_handoffs.find_one(
            {"organization_id": organization_id, "onboarding_handoff_id": onboarding_handoff_id},
            {"_id": 0},
        )
        return OnboardingHandoff(**doc) if doc else None

    async def list_onboarding_handoffs(
        self, organization_id: str, status: Optional[OnboardingHandoffStatus] = None
    ) -> list[OnboardingHandoff]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if status:
            query["status"] = status.value
        docs = await self.db.onboarding_handoffs.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
        return [OnboardingHandoff(**doc) for doc in docs]

    # offers
    async def upsert_offer(self, o: Offer) -> Offer:
        await self.db.offers.update_one(
            {"offer_id": o.offer_id}, {"$set": o.model_dump()}, upsert=True
        )
        return o

    async def get_offer(self, organization_id: str, offer_id: str) -> Optional[Offer]:
        doc = await self.db.offers.find_one(
            {"organization_id": organization_id, "offer_id": offer_id}, {"_id": 0}
        )
        return Offer(**doc) if doc else None

    async def list_offers(self, organization_id: str) -> list[Offer]:
        docs = await self.db.offers.find(
            {"organization_id": organization_id}, {"_id": 0}
        ).to_list(500)
        return [Offer(**d) for d in docs]

    async def upsert_communication_template(self, template: CandidateCommunicationTemplate) -> CandidateCommunicationTemplate:
        template.updated_at = utcnow_iso()
        await self.db.communication_templates.update_one(
            {"organization_id": template.organization_id, "communication_template_id": template.communication_template_id},
            {"$set": template.model_dump()}, upsert=True,
        )
        return template

    async def list_communication_templates(self, organization_id: str, *, active_only: bool = True) -> list[CandidateCommunicationTemplate]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if active_only:
            query["is_active"] = True
        docs = await self.db.communication_templates.find(query, {"_id": 0}).sort("name", 1).to_list(500)
        return [CandidateCommunicationTemplate(**doc) for doc in docs]

    # governed reusable communication content
    async def upsert_communication_template(self, template: CandidateCommunicationTemplate) -> CandidateCommunicationTemplate:
        template.updated_at = utcnow_iso()
        await self.db.communication_templates.update_one(
            {"organization_id": template.organization_id, "communication_template_id": template.communication_template_id},
            {"$set": template.model_dump()}, upsert=True,
        )
        return template

    async def list_communication_templates(self, organization_id: str, *, active_only: bool = True) -> list[CandidateCommunicationTemplate]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if active_only:
            query["is_active"] = True
        docs = await self.db.communication_templates.find(query, {"_id": 0}).sort("name", 1).to_list(500)
        return [CandidateCommunicationTemplate(**doc) for doc in docs]
