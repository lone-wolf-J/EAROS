"""EAROS Foundation Layer.

Contracts, value objects, identifiers, shared models, result types, errors, events.
Foundation NEVER imports domain modules. Every package depends on Foundation.
Nothing depends backwards.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

# ---------- Branded Identifiers (avoid primitive obsession) ----------

def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def new_organization_id() -> str: return _new_id("org")
def new_department_id() -> str: return _new_id("dept")
def new_team_id() -> str: return _new_id("team")
def new_job_id() -> str: return _new_id("job")
def new_requisition_id() -> str: return _new_id("req")
def new_candidate_id() -> str: return _new_id("cand")
def new_candidate_tag_id() -> str: return _new_id("ctag")
def new_application_id() -> str: return _new_id("app")
def new_pipeline_id() -> str: return _new_id("pipe")
def new_pipeline_stage_id() -> str: return _new_id("stage")
def new_talent_pool_id() -> str: return _new_id("pool")
def new_consent_id() -> str: return _new_id("consent")
def new_resume_id() -> str: return _new_id("resume")
def new_interview_id() -> str: return _new_id("interview")
def new_scorecard_id() -> str: return _new_id("scorecard")
def new_feedback_id() -> str: return _new_id("feedback")
def new_activity_id() -> str: return _new_id("activity")
def new_mention_id() -> str: return _new_id("mention")
def new_communication_id() -> str: return _new_id("comm")
def new_hiring_decision_id() -> str: return _new_id("hiredec")
def new_application_reactivation_request_id() -> str: return _new_id("appreact")
def new_offer_id() -> str: return _new_id("offer")
def new_skill_id() -> str: return _new_id("skill")
def new_policy_id() -> str: return _new_id("pol")
def new_capability_id() -> str: return _new_id("cap")
def new_decision_id() -> str: return _new_id("dec")
def new_execution_id() -> str: return _new_id("exec")
def new_plan_id() -> str: return _new_id("plan")
def new_step_id() -> str: return _new_id("step")
def new_event_id() -> str: return _new_id("evt")
def new_user_id() -> str: return _new_id("user")
def new_session_id() -> str: return _new_id("sess")
def new_approval_id() -> str: return _new_id("apr")
def new_reflection_id() -> str: return _new_id("refl")
def new_retention_case_id() -> str: return _new_id("ret")
def new_audit_export_id() -> str: return _new_id("auditexp")
def new_onboarding_handoff_id() -> str: return _new_id("handoff")
def new_notification_preference_id() -> str: return _new_id("notifpref")
def new_candidate_notification_delivery_id() -> str: return _new_id("candnotif")
def new_recruiter_alert_id() -> str: return _new_id("alert")
def new_data_subject_request_id() -> str: return _new_id("dsr")
def new_disposition_reason_id() -> str: return _new_id("dispreason")
def new_communication_template_id() -> str: return _new_id("commtemplate")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utcnow_iso() -> str:
    return utcnow().isoformat()


# ---------- Enums ----------

class Role(str, Enum):
    RECRUITER = "recruiter"
    HIRING_MANAGER = "hiring_manager"
    EXECUTIVE = "executive"
    CANDIDATE = "candidate"
    ADMIN = "admin"


class Sensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class PipelineStage(str, Enum):
    SOURCED = "sourced"
    SCREENING = "screening"
    PHONE_SCREEN = "phone_screen"
    TECHNICAL = "technical"
    ONSITE = "onsite"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class JobStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    ON_HOLD = "on_hold"
    FILLED = "filled"
    CANCELLED = "cancelled"


class RequisitionStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    OPEN = "open"
    ON_HOLD = "on_hold"
    FILLED = "filled"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class ApplicationStatus(str, Enum):
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"
    REJECTED = "rejected"
    HIRED = "hired"
    ARCHIVED = "archived"


class InterviewStatus(str, Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class ConsentStatus(str, Enum):
    GRANTED = "granted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class OfferStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    EXTENDED = "extended"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class RetentionCaseStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    ON_HOLD = "on_hold"
    APPROVED_FOR_ARCHIVE = "approved_for_archive"
    APPROVED_FOR_ERASURE = "approved_for_erasure"
    COMPLETED = "completed"
    REJECTED = "rejected"


class AuditExportStatus(str, Enum):
    REQUESTED = "requested"
    READY = "ready"
    EXPIRED = "expired"


class DataSubjectRequestStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    ON_HOLD = "on_hold"
    APPROVED = "approved"
    REJECTED = "rejected"
    FULFILLED = "fulfilled"


class OnboardingHandoffStatus(str, Enum):
    DRAFT = "draft"
    READY_FOR_HANDOFF = "ready_for_handoff"
    ACKNOWLEDGED = "acknowledged"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    POLICY_BLOCKED = "policy_blocked"


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class EventType(str, Enum):
    # Runtime
    PLAN_CREATED = "runtime.plan.created"
    EXECUTION_STARTED = "runtime.execution.started"
    EXECUTION_RESUMED = "runtime.execution.resumed"
    EXECUTION_COMPLETED = "runtime.execution.completed"
    EXECUTION_FAILED = "runtime.execution.failed"
    STEP_STARTED = "runtime.step.started"
    STEP_COMPLETED = "runtime.step.completed"
    # Policy
    POLICY_EVALUATED = "policy.evaluated"
    POLICY_VIOLATED = "policy.violated"
    # Governance
    APPROVAL_REQUESTED = "governance.approval.requested"
    APPROVAL_GRANTED = "governance.approval.granted"
    APPROVAL_DENIED = "governance.approval.denied"
    # World
    CANDIDATE_STAGE_CHANGED = "world.candidate.stage_changed"
    CANDIDATE_CREATED = "world.candidate.created"
    CANDIDATE_DEDUPLICATED = "world.candidate.deduplicated"
    CANDIDATE_CRM_UPDATED = "world.candidate.crm_updated"
    CANDIDATE_BULK_UPDATED = "world.candidate.bulk_updated"
    APPLICATION_CREATED = "world.application.created"
    CAREER_SITE_APPLICATION_RECEIVED = "world.career_site_application.received"
    APPLICATION_WITHDRAWN = "world.application.withdrawn"
    REFERRAL_INTAKE_RECORDED = "world.referral_intake.recorded"
    APPLICATION_STAGE_CHANGED = "world.application.stage_changed"
    APPLICATION_BULK_STAGE_CHANGED = "world.application.bulk_stage_changed"
    REQUISITION_CREATED = "world.requisition.created"
    REQUISITION_UPDATED = "world.requisition.updated"
    REQUISITION_PUBLICATION_UPDATED = "world.requisition.publication_updated"
    INTERVIEW_SCHEDULED = "world.interview.scheduled"
    SCORECARD_SUBMITTED = "world.scorecard.submitted"
    COLLABORATION_MENTION_CREATED = "world.collaboration_mention.created"
    CANDIDATE_COMMUNICATION_RECORDED = "world.candidate_communication.recorded"
    HIRING_DECISION_REQUESTED = "world.hiring_decision.requested"
    HIRING_DECISION_EFFECTIVE = "world.hiring_decision.effective"
    HIRING_DECISION_DENIED = "world.hiring_decision.denied"
    APPLICATION_REACTIVATION_REQUESTED = "world.application.reactivation_requested"
    APPLICATION_REACTIVATION_EFFECTIVE = "world.application.reactivation_effective"
    APPLICATION_REACTIVATION_DENIED = "world.application.reactivation_denied"
    CONSENT_RECORDED = "world.consent.recorded"
    NOTIFICATION_PREFERENCE_UPDATED = "world.notification_preference.updated"
    CANDIDATE_NOTIFICATION_RECORDED = "world.candidate_notification.recorded"
    RECRUITER_ALERT_CREATED = "world.recruiter_alert.created"
    RECRUITER_ALERT_READ = "world.recruiter_alert.read"
    OFFER_DRAFT_CREATED = "world.offer.draft_created"
    OFFER_EXTENDED = "world.offer.extended"
    JOB_CREATED = "world.job.created"
    RETENTION_CASE_REQUESTED = "world.retention_case.requested"
    RETENTION_CASE_DECIDED = "world.retention_case.decided"
    RETENTION_ARCHIVE_COMPLETED = "world.retention.archive_completed"
    RETENTION_ERASURE_COMPLETED = "world.retention.erasure_completed"
    DATA_SUBJECT_REQUESTED = "world.data_subject_request.requested"
    DATA_SUBJECT_REQUEST_DECIDED = "world.data_subject_request.decided"
    DATA_SUBJECT_REQUEST_FULFILLED = "world.data_subject_request.fulfilled"
    AUDIT_EXPORT_REQUESTED = "governance.audit_export.requested"
    ONBOARDING_HANDOFF_CREATED = "world.onboarding_handoff.created"
    ONBOARDING_HANDOFF_UPDATED = "world.onboarding_handoff.updated"
    APPLICATION_QUESTIONS_CONFIGURED = "world.application_questions.configured"
    APPLICATION_RESPONSES_CAPTURED = "world.application_responses.captured"
    DISPOSITION_REASON_CONFIGURED = "world.disposition_reason.configured"
    COMMUNICATION_TEMPLATE_CREATED = "world.communication_template.created"
    # Reflection
    REFLECTION_CREATED = "reflection.created"


# ---------- Value Objects ----------

class ConfidenceScore(BaseModel):
    """Confidence in an AI recommendation. 0.0..1.0 with band."""
    value: float = Field(ge=0.0, le=1.0)
    band: str = Field(description="LOW | MEDIUM | HIGH")

    @classmethod
    def from_value(cls, v: float) -> "ConfidenceScore":
        v = max(0.0, min(1.0, float(v)))
        band = "LOW"
        if v >= 0.80:
            band = "HIGH"
        elif v >= 0.55:
            band = "MEDIUM"
        return cls(value=round(v, 3), band=band)


class Evidence(BaseModel):
    """A piece of grounding evidence used by AI reasoning."""
    source: str
    reference: str
    excerpt: Optional[str] = None
    weight: float = 1.0


class ReasoningStep(BaseModel):
    step: int
    thought: str
    conclusion: Optional[str] = None


class PolicyReference(BaseModel):
    policy_id: str
    name: str
    decision: PolicyDecision
    reason: Optional[str] = None


class Recommendation(BaseModel):
    """Every AI output flows as a Recommendation. Never opaque."""
    decision_id: str = Field(default_factory=new_decision_id)
    title: str
    summary: str
    action: str  # capability id or human action
    inputs: dict[str, Any] = Field(default_factory=dict)
    confidence: ConfidenceScore
    reasoning: list[ReasoningStep] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    policies_referenced: list[PolicyReference] = Field(default_factory=list)
    created_at: str = Field(default_factory=utcnow_iso)


# ---------- Result Type ----------

T = TypeVar("T")


class Result(BaseModel, Generic[T]):
    ok: bool
    value: Optional[T] = None
    error: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def success(cls, value: T) -> "Result[T]":
        return cls(ok=True, value=value)

    @classmethod
    def failure(cls, error: str) -> "Result[T]":
        return cls(ok=False, error=error)


# ---------- Errors ----------

class EarosError(Exception):
    code: str = "EAROS_ERROR"


class PolicyViolationError(EarosError):
    code = "POLICY_VIOLATION"


class CapabilityNotFoundError(EarosError):
    code = "CAPABILITY_NOT_FOUND"


class ApprovalRequiredError(EarosError):
    code = "APPROVAL_REQUIRED"


# ---------- Base Event (immutable) ----------

class DomainEvent(BaseModel):
    """Immutable event. Persisted to append-only event stream for replay + audit."""
    model_config = ConfigDict(extra="ignore")

    event_id: str = Field(default_factory=new_event_id)
    event_type: EventType
    occurred_at: str = Field(default_factory=utcnow_iso)
    actor: Optional[str] = None  # user_id or "system" or capability_id
    subject_type: Optional[str] = None  # e.g., "candidate", "job", "execution"
    subject_id: Optional[str] = None
    organization_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None  # ties events for a single logical operation


# ---------- Simple domain base model ----------

class BaseDoc(BaseModel):
    model_config = ConfigDict(extra="ignore")
