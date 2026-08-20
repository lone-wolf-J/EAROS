"""EAROS — Enterprise Autonomous Recruitment Operating System.

FastAPI server that wires together:
- Foundation (types, IDs, events)
- Platform Core (Runtime, Planner, Policy, Capability Registry, World, Governance, Reflection)
- Intelligence Layer (Hiring, Offer, Organizational, Workforce, Strategy)
- Applications (Auth, Recruiter/Executive/Candidate/Dashboard endpoints)

Every route below is thin: it delegates business logic to platform + intelligence.
The LLM never executes business actions — all actions flow through the Runtime,
which enforces Policy and delegates to Capabilities.
"""
from __future__ import annotations

import asyncio
import hmac
import json
import logging
import os
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from applications.auth import AppUser, build_router as build_auth_router, get_current_user, validate_production_auth_configuration
from foundation import (
    AuditExportStatus,
    DataSubjectRequestStatus,
    DomainEvent,
    EventType,
    ExecutionStatus,
    PipelineStage,
    Role,
    Recommendation,
    Sensitivity,
    RetentionCaseStatus,
    new_execution_id,
    utcnow_iso,
)
from intelligence import (
    hiring_recommendations_for_job,
    hiring_strategy,
    offer_recommendation,
    organizational_health,
    skill_gap_analysis,
)
from intelligence.intake import run_intake, to_recommendation as intake_to_recommendation
from intelligence.sourcing import sourcing_sweep
from intelligence.resume_intel import (
    client_summary as resume_client_summary,
    fit_analysis as resume_fit,
    parse_resume as resume_parse,
    redact as resume_redact,
)
from intelligence.outreach_gen import draft_outreach_pack
from intelligence.screening_rubric import screen_candidate as screen_rubric
from intelligence.voice_interview import (
    start_interview as voice_start,
    summarize_interview as voice_summarize,
    turn as voice_turn,
)
from intelligence.simulation import simulate as sim_simulate
from intelligence.scenarios import (
    build_scenario_steps,
    list_scenarios,
    run_scenario,
    run_scenario_paced,
)
from intelligence.scenario_tracker import tracker as scenario_tracker
from platform_core.agents import AGENT_CATALOG, list_agents
from platform_core.capabilities import build_default_registry
from platform_core.governance import Approval, Governance
from platform_core.integrations import list_integrations, list_job_distribution_adapters as integration_job_distribution_adapters
from platform_core.live_activity import mission_snapshot
from platform_core.memory import Memory
from platform_core.planner import Planner
from platform_core.policy import Policy, PolicyContext, PolicyEngine
from platform_core.reflection import Reflection
from platform_core.replay import list_replayable_executions, replay_execution
from platform_core.runtime import ExecutionRecord, PlanStep, Runtime
from platform_core.world import (
    ActivityRecord,
    Application,
    AuditExportManifest,
    Candidate,
    CandidateNotificationDelivery,
    CandidateTag,
    CandidateCommunication,
    CandidateConsent,
    CollaborationMention,
    DataSubjectRequest,
    HiringDecision,
    Interview,
    InterviewFeedback,
    NotificationPreference,
    Offer,
    RecruiterAlert,
    OnboardingHandoff,
    Pipeline,
    PipelineStageDefinition,
    Requisition,
    RetentionCase,
    ResumeDocument,
    Scorecard,
    TalentPool,
    TalentPoolMembership,
    WorldState,
)
from seed import seed_all

class StructuredJsonFormatter(logging.Formatter):
    """Emit machine-readable operational events without request bodies or credentials."""

    _context_fields = ("event", "request_id", "method", "path", "status", "duration_ms", "error_type")

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": utcnow_iso(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
        }
        for field in self._context_fields:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"), default=str)


def _configure_operational_logging() -> None:
    """Configure one JSON stream for log aggregation, avoiding sensitive request content."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(StructuredJsonFormatter())
    root_logger.addHandler(stream_handler)
    root_logger.setLevel(os.getenv("EAROS_LOG_LEVEL", "INFO").upper())


_configure_operational_logging()
logger = logging.getLogger("earos")


class OperationalMetrics:
    """In-process, low-cardinality health signals suitable for a protected collector pull."""

    def __init__(self) -> None:
        self.started_at = utcnow_iso()
        self.request_count = 0
        self.failure_count = 0
        self.duration_ms_total = 0.0
        self.duration_ms_max = 0.0
        self.status_classes: Counter[str] = Counter()

    def record_completion(self, status_code: int, duration_ms: float) -> None:
        self.request_count += 1
        self.status_classes[f"{status_code // 100}xx"] += 1
        self.duration_ms_total += duration_ms
        self.duration_ms_max = max(self.duration_ms_max, duration_ms)

    def record_failure(self, duration_ms: float) -> None:
        self.failure_count += 1
        self.status_classes["5xx"] += 1
        self.duration_ms_total += duration_ms
        self.duration_ms_max = max(self.duration_ms_max, duration_ms)

    def snapshot(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "request_count": self.request_count,
            "failure_count": self.failure_count,
            "duration_ms_total": round(self.duration_ms_total, 2),
            "duration_ms_max": round(self.duration_ms_max, 2),
            "status_classes": dict(sorted(self.status_classes.items())),
        }


operational_metrics = OperationalMetrics()


def _env_flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}

# ---------- MongoDB ----------
mongo_url = os.environ["MONGO_URL"]
mongo_client = AsyncIOMotorClient(mongo_url)
db = mongo_client[os.environ["DB_NAME"]]

# ---------- Platform Core ----------
world = WorldState(db)
governance = Governance(db)
policy_engine = PolicyEngine(db, governance)
capability_registry = build_default_registry()
runtime = Runtime(db, world, capability_registry, policy_engine, governance)
planner = Planner(world, capability_registry)
memory = Memory(db)
reflection = Reflection(db, governance)

def _configured_cors_origins() -> list[str]:
    configured = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]
    production = os.getenv("EAROS_ENV", "development").lower() == "production"
    if production and (not configured or "*" in configured):
        raise RuntimeError("CORS_ORIGINS must be an explicit allowlist in production")
    return configured or ["http://localhost:3000", "http://localhost:3001"]


validate_production_auth_configuration()


app = FastAPI(
    title="EAROS",
    version=os.getenv("EAROS_VERSION", "0.1.0"),
    docs_url=None if os.getenv("EAROS_ENV", "development").lower() == "production" else "/docs",
    redoc_url=None if os.getenv("EAROS_ENV", "development").lower() == "production" else "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_configured_cors_origins(),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Session-ID", "X-Request-ID", "X-Bootstrap-Secret"],
)


@app.middleware("http")
async def request_correlation(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    started_at = time.perf_counter()
    try:
        response: Response = await call_next(request)
    except Exception as exc:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        operational_metrics.record_failure(duration_ms)
        logger.exception(
            "request_failed",
            extra={
                "event": "request_failed",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
                "error_type": type(exc).__name__,
            },
        )
        raise
    response.headers["X-Request-ID"] = request_id
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    operational_metrics.record_completion(response.status_code, duration_ms)
    logger.info(
        "request_completed",
        extra={
            "event": "request_completed",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


async def _current_user(request: Request) -> AppUser:
    return await get_current_user(request, db)


def _require_role(user: AppUser, *roles: Role) -> None:
    if user.role not in {role.value for role in roles}:
        raise HTTPException(status_code=403, detail="You do not have permission to perform this action")


async def _scoped_job(job_id: str, user: AppUser):
    job = await world.get_job(job_id)
    if not job or getattr(job, "organization_id", None) != user.organization_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


async def _scoped_candidate(candidate_id: str, user: AppUser):
    candidate = await world.get_candidate(candidate_id)
    if not candidate or getattr(candidate, "organization_id", None) != user.organization_id:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


async def _scoped_requisition(requisition_id: str, user: AppUser):
    requisition = await world.get_requisition(user.organization_id, requisition_id)
    if not requisition:
        raise HTTPException(status_code=404, detail="Requisition not found")
    return requisition


async def _scoped_application(application_id: str, user: AppUser):
    application = await world.get_application(user.organization_id, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


# ---------- Auth router ----------
app.include_router(build_auth_router(db))


# ============================================================
#   HEALTH + BOOTSTRAP
# ============================================================

@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "service": "EAROS",
        "kind": "liveness",
        "version": app.version,
        "time": utcnow_iso(),
    }


@app.get("/api/ready", include_in_schema=False)
async def readiness():
    try:
        await db.command("ping")
    except Exception as exc:
        logger.warning("readiness_failed", extra={"event": "readiness_failed", "error_type": type(exc).__name__})
        raise HTTPException(status_code=503, detail="EAROS dependencies are not ready")
    return {"ok": True, "service": "EAROS", "kind": "readiness", "version": app.version, "time": utcnow_iso()}


@app.get("/api/metrics", include_in_schema=False)
async def metrics(x_operations_token: Optional[str] = Header(default=None)):
    """Return bounded, non-tenant operational counters to an authorized collector."""
    configured_token = os.getenv("EAROS_OPERATIONS_METRICS_TOKEN")
    if not configured_token or not x_operations_token or not hmac.compare_digest(x_operations_token, configured_token):
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "service": "EAROS",
        "version": app.version,
        "observed_at": utcnow_iso(),
        "metrics": operational_metrics.snapshot(),
    }


@app.get("/api/user-guide.pdf", include_in_schema=False)
async def user_guide_pdf():
    """Serve the pre-built PDF user guide as a download."""
    path = "/app/EAROS_User_Guide.pdf"
    if not os.path.exists(path):
        raise HTTPException(404, "user guide PDF not yet built")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename="EAROS_User_Guide.pdf",
    )


@app.post("/api/bootstrap", include_in_schema=False)
async def bootstrap(x_bootstrap_secret: Optional[str] = Header(default=None)):
    """Seed World State + policies + demo users. Idempotent."""
    expected_secret = os.getenv("EAROS_BOOTSTRAP_SECRET")
    if not _env_flag("EAROS_ENABLE_BOOTSTRAP_ENDPOINT", False) or not expected_secret:
        raise HTTPException(status_code=404, detail="Not found")
    if not x_bootstrap_secret or not hmac.compare_digest(x_bootstrap_secret, expected_secret):
        raise HTTPException(status_code=403, detail="Bootstrap authorization failed")
    result = await seed_all(db)
    return {"ok": True, "seeded": result}


# ============================================================
#   WORLD STATE (read-only unless via runtime)
# ============================================================

@app.get("/api/world/organization")
async def get_org(user: AppUser = Depends(_current_user)):
    org = await world.get_organization(user.organization_id)
    if not org:
        raise HTTPException(404, "organization not found")
    return org.model_dump()


@app.get("/api/world/departments")
async def list_departments(user: AppUser = Depends(_current_user)):
    return [d.model_dump() for d in await world.list_departments(user.organization_id)]


@app.get("/api/world/teams")
async def list_teams(user: AppUser = Depends(_current_user)):
    return [t.model_dump() for t in await world.list_teams(user.organization_id)]


@app.get("/api/world/skills")
async def list_skills(user: AppUser = Depends(_current_user)):
    return [s.model_dump() for s in await world.list_skills()]


@app.get("/api/world/jobs")
async def list_jobs(user: AppUser = Depends(_current_user)):
    return [j.model_dump() for j in await world.list_jobs(user.organization_id)]


@app.get("/api/world/jobs/{job_id}")
async def get_job(job_id: str, user: AppUser = Depends(_current_user)):
    j = await _scoped_job(job_id, user)
    return j.model_dump()


@app.get("/api/world/jobs/{job_id}/candidates")
async def list_job_candidates(
    job_id: str,
    stage: Optional[str] = None,
    user: AppUser = Depends(_current_user),
):
    await _scoped_job(job_id, user)
    stage_enum = PipelineStage(stage) if stage else None
    cands = await world.list_candidates(user.organization_id, job_id=job_id, stage=stage_enum)
    return [c.model_dump() for c in cands]


@app.get("/api/world/candidates")
async def list_all_candidates(
    stage: Optional[str] = None,
    user: AppUser = Depends(_current_user),
):
    stage_enum = PipelineStage(stage) if stage else None
    cands = await world.list_candidates(user.organization_id, stage=stage_enum)
    return [c.model_dump() for c in cands]


@app.get("/api/world/candidates/{candidate_id}")
async def get_candidate(candidate_id: str, user: AppUser = Depends(_current_user)):
    c = await _scoped_candidate(candidate_id, user)
    return c.model_dump()


class StageTransitionRequest(BaseModel):
    stage: str
    reason: Optional[str] = None


@app.post("/api/world/candidates/{candidate_id}/stage")
async def set_candidate_stage_ep(
    candidate_id: str,
    req: StageTransitionRequest,
    user: AppUser = Depends(_current_user),
):
    _require_role(user, Role.ADMIN, Role.RECRUITER, Role.HIRING_MANAGER)
    c = await _scoped_candidate(candidate_id, user)
    try:
        new_stage = PipelineStage(req.stage)
    except ValueError:
        raise HTTPException(400, f"invalid stage: {req.stage}")

    old_stage = c.stage
    await world.set_candidate_stage(candidate_id, new_stage)

    # Emit an immutable event so the transition shows up in Governance audit
    from foundation import DomainEvent
    await governance.emit(DomainEvent(
        event_type=EventType.CANDIDATE_STAGE_CHANGED,
        actor=f"recruiter:{user.user_id}",
        subject_type="candidate",
        subject_id=candidate_id,
        organization_id=user.organization_id,
        payload={
            "action": "manual_stage_transition",
            "from": old_stage.value,
            "to": new_stage.value,
            "reason": req.reason or "manual override by recruiter",
        },
    ))
    updated = await world.get_candidate(candidate_id)
    return updated.model_dump()


@app.get("/api/world/offers")
async def list_offers(user: AppUser = Depends(_current_user)):
    return [o.model_dump() for o in await world.list_offers(user.organization_id)]


# ============================================================
#   ENTERPRISE ATS — direct human operations, always audited
# ============================================================

class PipelineUpsertRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: Optional[str] = Field(default=None, max_length=2000)
    stages: list[PipelineStageDefinition] = Field(min_length=1, max_length=30)
    is_default: bool = False


class OnboardingHandoffCreateRequest(BaseModel):
    offer_id: str = Field(min_length=3, max_length=160)
    candidate_id: str = Field(min_length=3, max_length=160)
    job_id: str = Field(min_length=3, max_length=160)
    application_id: Optional[str] = Field(default=None, max_length=160)
    target_start_date: Optional[str] = Field(default=None, max_length=80)
    owner_user_id: Optional[str] = Field(default=None, max_length=160)
    destination_system: Optional[str] = Field(default=None, max_length=160)
    checklist: list[dict[str, Any]] = Field(default_factory=list, max_length=50)


@app.get("/api/ats/pipelines")
async def list_ats_pipelines(user: AppUser = Depends(_current_user)):
    return [pipeline.model_dump() for pipeline in await world.list_pipelines(user.organization_id)]


@app.post("/api/ats/pipelines")
async def create_ats_pipeline(req: PipelineUpsertRequest, user: AppUser = Depends(_current_user)):
    _require_role(user, Role.ADMIN, Role.RECRUITER)
    if len({stage.name.strip().lower() for stage in req.stages}) != len(req.stages):
        raise HTTPException(status_code=400, detail="Pipeline stage names must be unique")
    if len({stage.order for stage in req.stages}) != len(req.stages):
        raise HTTPException(status_code=400, detail="Pipeline stage order values must be unique")
    pipeline = await world.upsert_pipeline(Pipeline(organization_id=user.organization_id, **req.model_dump()))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="pipeline",
        entity_id=pipeline.pipeline_id,
        event_type="pipeline.created",
        actor_user_id=user.user_id,
        payload={"name": pipeline.name, "stage_count": len(pipeline.stages)},
    ))
    return pipeline.model_dump()


class RequisitionCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    department_id: Optional[str] = None
    team_id: Optional[str] = None
    hiring_manager_id: Optional[str] = None
    recruiter_ids: list[str] = Field(default_factory=list, max_length=50)
    headcount: int = Field(default=1, ge=1, le=1000)
    employment_type: str = Field(default="full_time", max_length=80)
    location: Optional[str] = Field(default=None, max_length=200)
    target_start_date: Optional[str] = None
    target_close_date: Optional[str] = None
    hiring_plan: dict[str, Any] = Field(default_factory=dict)
    pipeline_id: Optional[str] = None
    job_id: Optional[str] = None


class RequisitionPublicationUpdateRequest(BaseModel):
    internal_publication_status: Optional[str] = Field(default=None, pattern="^(draft|published|closed)$")
    external_publication_status: Optional[str] = Field(default=None, pattern="^(not_requested|draft_ready|pending_approval)$")
    external_publication_targets: Optional[list[str]] = Field(default=None, max_length=12)
    career_site_enabled: Optional[bool] = None
    referral_intake_enabled: Optional[bool] = None


@app.get("/api/ats/requisitions")
async def list_ats_requisitions(user: AppUser = Depends(_current_user)):
    return [requisition.model_dump() for requisition in await world.list_requisitions(user.organization_id)]


@app.post("/api/ats/requisitions")
async def create_ats_requisition(req: RequisitionCreateRequest, user: AppUser = Depends(_current_user)):
    _require_role(user, Role.ADMIN, Role.RECRUITER)
    if req.pipeline_id and not await world.get_pipeline(user.organization_id, req.pipeline_id):
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if req.job_id:
        await _scoped_job(req.job_id, user)
    requisition = await world.upsert_requisition(Requisition(
        organization_id=user.organization_id,
        created_by_user_id=user.user_id,
        **req.model_dump(),
    ))
    from foundation import DomainEvent
    await governance.emit(DomainEvent(
        event_type=EventType.REQUISITION_CREATED,
        actor=f"user:{user.user_id}",
        subject_type="requisition",
        subject_id=requisition.requisition_id,
        organization_id=user.organization_id,
        payload={"title": requisition.title, "headcount": requisition.headcount},
    ))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="requisition",
        entity_id=requisition.requisition_id,
        event_type="requisition.created",
        actor_user_id=user.user_id,
        payload={"title": requisition.title},
    ))
    return requisition.model_dump()


@app.patch("/api/ats/requisitions/{requisition_id}/publication")
async def update_ats_requisition_publication(
    requisition_id: str, req: RequisitionPublicationUpdateRequest, user: AppUser = Depends(_current_user)
):
    """Persist recruiter-managed publication readiness; no external delivery occurs here."""
    _require_role(user, Role.ADMIN, Role.RECRUITER)
    requisition = await _scoped_requisition(requisition_id, user)
    update = req.model_dump(exclude_none=True)
    targets = update.get("external_publication_targets")
    if targets is not None:
        allowed = {adapter.provider for adapter in integration_job_distribution_adapters()}
        invalid = sorted(set(targets) - allowed)
        if invalid:
            raise HTTPException(status_code=400, detail=f"Unsupported job-distribution provider: {invalid[0]}")
        update["external_publication_targets"] = sorted(set(targets))
    for field, value in update.items():
        setattr(requisition, field, value)
    requisition = await world.upsert_requisition(requisition)
    await governance.emit(DomainEvent(
        event_type=EventType.REQUISITION_PUBLICATION_UPDATED,
        actor=f"user:{user.user_id}",
        subject_type="requisition",
        subject_id=requisition.requisition_id,
        organization_id=user.organization_id,
        payload={"internal_status": requisition.internal_publication_status, "external_status": requisition.external_publication_status, "targets": requisition.external_publication_targets},
    ))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="requisition",
        entity_id=requisition.requisition_id,
        event_type="requisition.publication_updated",
        actor_user_id=user.user_id,
        payload={"internal_status": requisition.internal_publication_status, "external_status": requisition.external_publication_status, "target_count": len(requisition.external_publication_targets)},
    ))
    return requisition.model_dump()


class CandidateCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: Optional[str] = Field(default=None, max_length=320)
    phone: Optional[str] = Field(default=None, max_length=64)
    linkedin_url: Optional[str] = Field(default=None, max_length=1000)
    job_id: Optional[str] = None
    location: str = Field(default="", max_length=200)
    country: str = Field(default="", max_length=100)
    current_title: str = Field(default="", max_length=200)
    current_company: str = Field(default="", max_length=200)
    years_experience: float = Field(default=0, ge=0, le=100)
    expected_salary: int = Field(default=0, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    skills: list[str] = Field(default_factory=list, max_length=250)
    source: str = Field(default="manual", max_length=80)
    source_detail: Optional[str] = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=100)


@app.post("/api/ats/candidates")
async def create_ats_candidate(req: CandidateCreateRequest, user: AppUser = Depends(_current_user)):
    _require_role(user, Role.ADMIN, Role.RECRUITER)
    if req.job_id:
        await _scoped_job(req.job_id, user)
    duplicate = await world.find_duplicate_candidate(
        user.organization_id, email=req.email, phone=req.phone, linkedin_url=req.linkedin_url
    )
    if duplicate:
        raise HTTPException(status_code=409, detail={"message": "Candidate already exists", "candidate_id": duplicate.candidate_id})
    candidate = await world.upsert_candidate(Candidate(organization_id=user.organization_id, **req.model_dump()))
    from foundation import DomainEvent
    await governance.emit(DomainEvent(
        event_type=EventType.CANDIDATE_CREATED,
        actor=f"user:{user.user_id}",
        subject_type="candidate",
        subject_id=candidate.candidate_id,
        organization_id=user.organization_id,
        payload={"source": candidate.source, "job_id": candidate.job_id},
    ))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="candidate",
        entity_id=candidate.candidate_id,
        event_type="candidate.created",
        actor_user_id=user.user_id,
        payload={"source": candidate.source},
    ))
    return candidate.model_dump()


@app.get("/api/ats/candidates")
async def search_ats_candidates(
    q: Optional[str] = Query(default=None, max_length=300),
    tag: list[str] = Query(default=[]),
    source: Optional[str] = Query(default=None, max_length=80),
    minimum_fit_score: Optional[float] = Query(default=None, ge=0, le=1),
    user: AppUser = Depends(_current_user),
):
    candidates = await world.search_candidates(
        user.organization_id,
        query=q,
        tags=tag,
        source=source,
        minimum_fit_score=minimum_fit_score,
    )
    return [candidate.model_dump() for candidate in candidates]


class CandidateTagRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str = Field(default="slate", max_length=40)
    description: Optional[str] = Field(default=None, max_length=500)


@app.get("/api/ats/candidate-tags")
async def list_ats_candidate_tags(user: AppUser = Depends(_current_user)):
    return [tag.model_dump() for tag in await world.list_candidate_tags(user.organization_id)]


@app.post("/api/ats/candidate-tags")
async def create_ats_candidate_tag(req: CandidateTagRequest, user: AppUser = Depends(_current_user)):
    _require_role(user, Role.ADMIN, Role.RECRUITER)
    name = " ".join(req.name.split())
    tag = await world.upsert_candidate_tag(CandidateTag(
        organization_id=user.organization_id,
        name=name,
        normalized_name=name.lower(),
        color=req.color,
        description=req.description,
        created_by_user_id=user.user_id,
    ))
    return tag.model_dump()


class CandidateBulkActionRequest(BaseModel):
    candidate_ids: list[str] = Field(min_length=1, max_length=200)
    action: str = Field(pattern="^(add_tags|remove_tags|set_source|add_to_talent_pool|archive)$")
    tags: list[str] = Field(default_factory=list, max_length=100)
    source: Optional[str] = Field(default=None, max_length=80)
    source_detail: Optional[str] = Field(default=None, max_length=500)
    talent_pool_id: Optional[str] = None
    note: Optional[str] = Field(default=None, max_length=1000)


@app.post("/api/ats/candidates/bulk")
async def bulk_update_ats_candidates(req: CandidateBulkActionRequest, user: AppUser = Depends(_current_user)):
    _require_role(user, Role.ADMIN, Role.RECRUITER)
    candidate_ids = list(dict.fromkeys(req.candidate_ids))
    candidates = [await _scoped_candidate(candidate_id, user) for candidate_id in candidate_ids]
    if req.action in {"add_tags", "remove_tags"} and not req.tags:
        raise HTTPException(status_code=400, detail="At least one tag is required")
    if req.action == "set_source" and not req.source:
        raise HTTPException(status_code=400, detail="A source is required")
    if req.action == "add_to_talent_pool":
        if not req.talent_pool_id:
            raise HTTPException(status_code=400, detail="A talent pool is required")
        pool_exists = any(pool.talent_pool_id == req.talent_pool_id for pool in await world.list_talent_pools(user.organization_id))
        if not pool_exists:
            raise HTTPException(status_code=404, detail="Talent pool not found")
    updated: list[Candidate] = []
    for candidate in candidates:
        if req.action == "add_tags":
            candidate = await world.update_candidate_crm(
                user.organization_id, candidate.candidate_id, tags=[*candidate.tags, *req.tags]
            )
        elif req.action == "remove_tags":
            remove_tags = {tag.lower() for tag in req.tags}
            candidate = await world.update_candidate_crm(
                user.organization_id, candidate.candidate_id,
                tags=[tag for tag in candidate.tags if tag.lower() not in remove_tags],
            )
        elif req.action == "set_source":
            candidate = await world.update_candidate_crm(
                user.organization_id, candidate.candidate_id, source=req.source, source_detail=req.source_detail
            )
        elif req.action == "add_to_talent_pool":
            await world.add_to_talent_pool(TalentPoolMembership(
                organization_id=user.organization_id,
                talent_pool_id=req.talent_pool_id,
                candidate_id=candidate.candidate_id,
                added_by_user_id=user.user_id,
                note=req.note,
            ))
        elif req.action == "archive":
            candidate = await world.update_candidate_crm(
                user.organization_id, candidate.candidate_id, archived_at=utcnow_iso()
            )
        await world.record_activity(ActivityRecord(
            organization_id=user.organization_id,
            entity_type="candidate",
            entity_id=candidate.candidate_id,
            event_type="candidate.bulk_updated",
            actor_user_id=user.user_id,
            payload={"action": req.action, "tags": req.tags, "source": req.source, "talent_pool_id": req.talent_pool_id},
        ))
        await governance.emit(DomainEvent(
            event_type=EventType.CANDIDATE_BULK_UPDATED,
            actor=f"user:{user.user_id}",
            subject_type="candidate",
            subject_id=candidate.candidate_id,
            organization_id=user.organization_id,
            payload={"action": req.action},
        ))
        updated.append(candidate)
    return {"updated_count": len(updated), "candidates": [candidate.model_dump() for candidate in updated]}


class ApplicationCreateRequest(BaseModel):
    candidate_id: str
    requisition_id: Optional[str] = None
    job_id: Optional[str] = None
    pipeline_id: Optional[str] = None
    current_stage_id: Optional[str] = None
    current_stage_name: str = Field(default="Applied", min_length=1, max_length=120)
    source: str = Field(default="manual", max_length=80)
    source_detail: Optional[str] = Field(default=None, max_length=500)
    referral_user_id: Optional[str] = None


class CareerSiteApplicationRequest(BaseModel):
    """Public data accepted only for an explicitly enabled career-site requisition."""
    organization_id: str = Field(min_length=3, max_length=200)
    full_name: str = Field(min_length=2, max_length=200)
    email: Optional[str] = Field(default=None, max_length=320)
    phone: Optional[str] = Field(default=None, max_length=64)
    linkedin_url: Optional[str] = Field(default=None, max_length=1000)
    location: str = Field(default="", max_length=200)
    current_title: str = Field(default="", max_length=200)
    current_company: str = Field(default="", max_length=200)
    years_experience: float = Field(default=0, ge=0, le=100)
    skills: list[str] = Field(default_factory=list, max_length=250)
    consent_to_recruit: bool = False


class ReferralIntakeRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: Optional[str] = Field(default=None, max_length=320)
    phone: Optional[str] = Field(default=None, max_length=64)
    linkedin_url: Optional[str] = Field(default=None, max_length=1000)
    location: str = Field(default="", max_length=200)
    current_title: str = Field(default="", max_length=200)
    current_company: str = Field(default="", max_length=200)
    years_experience: float = Field(default=0, ge=0, le=100)
    skills: list[str] = Field(default_factory=list, max_length=250)
    referrer_user_id: str = Field(min_length=3, max_length=200)
    note: Optional[str] = Field(default=None, max_length=2000)


@app.get("/api/ats/applications")
async def list_ats_applications(
    requisition_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
    user: AppUser = Depends(_current_user),
):
    return [application.model_dump() for application in await world.list_applications(
        user.organization_id, requisition_id=requisition_id, candidate_id=candidate_id
    )]


@app.post("/api/ats/applications")
async def create_ats_application(req: ApplicationCreateRequest, user: AppUser = Depends(_current_user)):
    _require_role(user, Role.ADMIN, Role.RECRUITER)
    await _scoped_candidate(req.candidate_id, user)
    if req.requisition_id:
        await _scoped_requisition(req.requisition_id, user)
    if req.job_id:
        await _scoped_job(req.job_id, user)
    if req.pipeline_id and not await world.get_pipeline(user.organization_id, req.pipeline_id):
        raise HTTPException(status_code=404, detail="Pipeline not found")
    existing = await world.list_applications(
        user.organization_id, candidate_id=req.candidate_id, requisition_id=req.requisition_id
    )
    if req.requisition_id and any(application.status.value == "active" for application in existing):
        raise HTTPException(status_code=409, detail="Candidate already has an active application for this requisition")
    now = utcnow_iso()
    application = await world.upsert_application(Application(
        organization_id=user.organization_id,
        stage_history=[{"stage_id": req.current_stage_id, "stage_name": req.current_stage_name, "changed_at": now, "actor_user_id": user.user_id}],
        **req.model_dump(),
    ))
    from foundation import DomainEvent
    await governance.emit(DomainEvent(
        event_type=EventType.APPLICATION_CREATED,
        actor=f"user:{user.user_id}",
        subject_type="application",
        subject_id=application.application_id,
        organization_id=user.organization_id,
        payload={"candidate_id": application.candidate_id, "requisition_id": application.requisition_id},
    ))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="application",
        entity_id=application.application_id,
        event_type="application.created",
        actor_user_id=user.user_id,
        payload={"candidate_id": application.candidate_id},
    ))
    return application.model_dump()


class OfferDraftCreateRequest(BaseModel):
    """Create an internal offer draft; approval and delivery are separate governed operations."""
    candidate_id: str = Field(min_length=3, max_length=200)
    job_id: str = Field(min_length=3, max_length=200)
    base_salary: int = Field(ge=0, le=10_000_000)
    bonus: int = Field(default=0, ge=0, le=10_000_000)
    equity_units: int = Field(default=0, ge=0, le=10_000_000)
    signing_bonus: int = Field(default=0, ge=0, le=10_000_000)
    currency: str = Field(min_length=3, max_length=3, pattern="^[A-Z]{3}$")


@app.get("/api/ats/offers")
async def list_ats_offers(user: AppUser = Depends(_current_user)):
    return [offer.model_dump() for offer in await world.list_offers(user.organization_id)]


@app.post("/api/ats/offers")
async def create_ats_offer_draft(req: OfferDraftCreateRequest, user: AppUser = Depends(_current_user)):
    _require_role(user, Role.ADMIN, Role.RECRUITER)
    await _scoped_candidate(req.candidate_id, user)
    await _scoped_job(req.job_id, user)
    offer = await world.upsert_offer(Offer(organization_id=user.organization_id, **req.model_dump()))
    await governance.emit(DomainEvent(
        event_type=EventType.OFFER_DRAFT_CREATED,
        actor=f"user:{user.user_id}",
        subject_type="offer",
        subject_id=offer.offer_id,
        organization_id=user.organization_id,
        payload={"candidate_id": offer.candidate_id, "job_id": offer.job_id, "status": offer.status.value},
    ))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="candidate",
        entity_id=offer.candidate_id,
        event_type="offer.draft_created",
        actor_user_id=user.user_id,
        payload={"offer_id": offer.offer_id, "job_id": offer.job_id, "status": offer.status.value},
    ))
    return offer.model_dump()


def _career_site_requisition_is_open(requisition: Requisition) -> bool:
    """Public submissions require an explicitly enabled, open, non-archived requisition."""
    approval_status = getattr(requisition.approval_status, "value", requisition.approval_status)
    return bool(
        requisition.career_site_enabled
        and requisition.internal_publication_status == "published"
        and approval_status == "open"
        and not requisition.archived_at
    )


@app.get("/api/public/ats/career-sites/{organization_id}/requisitions")
async def list_public_career_site_requisitions(organization_id: str):
    """Return only enabled public requisition metadata; never private plans or candidate data."""
    requisitions = await world.list_requisitions(organization_id)
    return [
        {
            "requisition_id": requisition.requisition_id,
            "title": requisition.title,
            "employment_type": requisition.employment_type,
            "location": requisition.location,
            "department_id": requisition.department_id,
            "target_close_date": requisition.target_close_date,
        }
        for requisition in requisitions if _career_site_requisition_is_open(requisition)
    ]


@app.post("/api/public/ats/requisitions/{requisition_id}/applications", status_code=201)
async def submit_career_site_application(requisition_id: str, req: CareerSiteApplicationRequest):
    """Record a consented public application without triggering automation or outbound contact."""
    requisition = await world.get_requisition(req.organization_id, requisition_id)
    if not requisition or not _career_site_requisition_is_open(requisition):
        raise HTTPException(status_code=404, detail="Career-site requisition not available")
    if not req.consent_to_recruit:
        raise HTTPException(status_code=409, detail="Recruiting consent is required before submitting a career-site application")
    candidate = await world.find_duplicate_candidate(
        req.organization_id, email=req.email, phone=req.phone, linkedin_url=req.linkedin_url
    )
    candidate_created = candidate is None
    if candidate_created:
        candidate = await world.upsert_candidate(Candidate(
            organization_id=req.organization_id,
            full_name=req.full_name,
            email=req.email,
            phone=req.phone,
            linkedin_url=req.linkedin_url,
            location=req.location,
            current_title=req.current_title,
            current_company=req.current_company,
            years_experience=req.years_experience,
            skills=req.skills,
            source="career_site",
            source_detail=f"career_site:{requisition_id}",
        ))
        await governance.emit(DomainEvent(
            event_type=EventType.CANDIDATE_CREATED,
            actor="public:career_site",
            subject_type="candidate",
            subject_id=candidate.candidate_id,
            organization_id=req.organization_id,
            payload={"source": "career_site", "requisition_id": requisition_id},
        ))
        await world.record_activity(ActivityRecord(
            organization_id=req.organization_id,
            entity_type="candidate",
            entity_id=candidate.candidate_id,
            event_type="candidate.career_site_created",
            actor_user_id=None,
            payload={"requisition_id": requisition_id},
        ))
    consent = await world.upsert_consent(CandidateConsent(
        organization_id=req.organization_id,
        candidate_id=candidate.candidate_id,
        purpose="recruiting",
        legal_basis="candidate_submitted_career_site_application",
        captured_from="career_site",
        recorded_by_user_id=None,
    ))
    existing = await world.list_applications(
        req.organization_id, candidate_id=candidate.candidate_id, requisition_id=requisition_id
    )
    if any(application.status.value == "active" for application in existing):
        raise HTTPException(status_code=409, detail="An active application already exists for this requisition")
    now = utcnow_iso()
    application = await world.upsert_application(Application(
        organization_id=req.organization_id,
        candidate_id=candidate.candidate_id,
        requisition_id=requisition_id,
        pipeline_id=requisition.pipeline_id,
        current_stage_name="Applied",
        source="career_site",
        source_detail=f"career_site:{requisition_id}",
        stage_history=[{"stage_id": None, "stage_name": "Applied", "changed_at": now, "actor_user_id": "public:career_site"}],
    ))
    await governance.emit(DomainEvent(
        event_type=EventType.CAREER_SITE_APPLICATION_RECEIVED,
        actor="public:career_site",
        subject_type="application",
        subject_id=application.application_id,
        organization_id=req.organization_id,
        payload={"candidate_id": candidate.candidate_id, "requisition_id": requisition_id, "consent_id": consent.consent_id, "candidate_created": candidate_created},
    ))
    await world.record_activity(ActivityRecord(
        organization_id=req.organization_id,
        entity_type="application",
        entity_id=application.application_id,
        event_type="application.career_site_received",
        actor_user_id=None,
        payload={"candidate_id": candidate.candidate_id, "requisition_id": requisition_id, "consent_id": consent.consent_id},
    ))
    return {"application_id": application.application_id, "received_at": application.applied_at, "status": "received"}


@app.post("/api/ats/requisitions/{requisition_id}/referrals", status_code=201)
async def record_ats_referral_intake(
    requisition_id: str, req: ReferralIntakeRequest, user: AppUser = Depends(_current_user)
):
    """Record an authenticated employee referral; the endpoint never sends outreach."""
    _require_role(user, Role.ADMIN, Role.RECRUITER, Role.HIRING_MANAGER)
    requisition = await _scoped_requisition(requisition_id, user)
    if not requisition.referral_intake_enabled or requisition.archived_at:
        raise HTTPException(status_code=409, detail="Referral intake is not enabled for this requisition")
    if user.role == Role.HIRING_MANAGER and req.referrer_user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Hiring managers may record only their own referrals")
    referrer = await db.users.find_one(
        {"user_id": req.referrer_user_id, "organization_id": user.organization_id}, {"_id": 0}
    )
    if not referrer:
        raise HTTPException(status_code=404, detail="Referrer not found in this organization")
    candidate = await world.find_duplicate_candidate(
        user.organization_id, email=req.email, phone=req.phone, linkedin_url=req.linkedin_url
    )
    candidate_created = candidate is None
    if candidate_created:
        candidate = await world.upsert_candidate(Candidate(
            organization_id=user.organization_id,
            full_name=req.full_name,
            email=req.email,
            phone=req.phone,
            linkedin_url=req.linkedin_url,
            location=req.location,
            current_title=req.current_title,
            current_company=req.current_company,
            years_experience=req.years_experience,
            skills=req.skills,
            source="referral",
            source_detail=f"employee_referral:{req.referrer_user_id}",
        ))
    existing = await world.list_applications(
        user.organization_id, candidate_id=candidate.candidate_id, requisition_id=requisition_id
    )
    if any(application.status.value == "active" for application in existing):
        raise HTTPException(status_code=409, detail="An active application already exists for this requisition")
    now = utcnow_iso()
    application = await world.upsert_application(Application(
        organization_id=user.organization_id,
        candidate_id=candidate.candidate_id,
        requisition_id=requisition_id,
        pipeline_id=requisition.pipeline_id,
        current_stage_name="Applied",
        source="referral",
        source_detail=f"employee_referral:{req.referrer_user_id}",
        referral_user_id=req.referrer_user_id,
        stage_history=[{"stage_id": None, "stage_name": "Applied", "changed_at": now, "actor_user_id": user.user_id}],
    ))
    await governance.emit(DomainEvent(
        event_type=EventType.REFERRAL_INTAKE_RECORDED,
        actor=f"user:{user.user_id}",
        subject_type="application",
        subject_id=application.application_id,
        organization_id=user.organization_id,
        payload={"candidate_id": candidate.candidate_id, "requisition_id": requisition_id, "referrer_user_id": req.referrer_user_id, "candidate_created": candidate_created},
    ))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="candidate",
        entity_id=candidate.candidate_id,
        event_type="candidate.referral_intake_recorded",
        actor_user_id=user.user_id,
        payload={"requisition_id": requisition_id, "application_id": application.application_id, "referrer_user_id": req.referrer_user_id, "note": req.note},
    ))
    return {"application": application.model_dump(), "candidate_created": candidate_created}


class ApplicationStageRequest(BaseModel):
    stage_id: Optional[str] = None
    stage_name: str = Field(min_length=1, max_length=120)
    reason: Optional[str] = Field(default=None, max_length=1000)


_FALLBACK_ACTIVE_APPLICATION_STAGES = frozenset({"Applied", "Screened", "Interview", "Offer"})
_TERMINAL_APPLICATION_STAGE_NAMES = frozenset({"Hired", "Rejected"})


async def _validate_application_stage_transition(application: Application, req: ApplicationStageRequest) -> None:
    """Allow only active pipeline movement; terminal outcomes require a governed hiring decision."""
    application_status = getattr(application.status, "value", application.status)
    if application_status != "active":
        raise HTTPException(status_code=409, detail="Only active applications can move through the pipeline")
    if req.stage_name in _TERMINAL_APPLICATION_STAGE_NAMES:
        raise HTTPException(
            status_code=409,
            detail="Hired and Rejected outcomes require an approval-gated hiring decision",
        )

    if not application.pipeline_id:
        if req.stage_name not in _FALLBACK_ACTIVE_APPLICATION_STAGES:
            raise HTTPException(status_code=400, detail="Application stage is not part of the canonical active pipeline")
        return

    pipeline = await world.get_pipeline(application.organization_id, application.pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=409, detail="Application pipeline is unavailable")
    matches = [
        stage for stage in pipeline.stages
        if (req.stage_id and stage.stage_id == req.stage_id) or (not req.stage_id and stage.name == req.stage_name)
    ]
    if len(matches) != 1:
        raise HTTPException(status_code=400, detail="Application stage is not configured for this pipeline")
    stage = matches[0]
    if stage.name != req.stage_name:
        raise HTTPException(status_code=400, detail="Application stage identifier and name do not match")
    if stage.category.startswith("terminal_"):
        raise HTTPException(
            status_code=409,
            detail="Terminal pipeline stages require an approval-gated hiring decision",
        )


@app.post("/api/ats/applications/{application_id}/stage")
async def move_ats_application_stage(
    application_id: str, req: ApplicationStageRequest, user: AppUser = Depends(_current_user)
):
    _require_role(user, Role.ADMIN, Role.RECRUITER)
    application = await _scoped_application(application_id, user)
    await _validate_application_stage_transition(application, req)
    previous_name = application.current_stage_name
    application.current_stage_id = req.stage_id
    application.current_stage_name = req.stage_name
    application.stage_history.append({
        "stage_id": req.stage_id,
        "stage_name": req.stage_name,
        "changed_at": utcnow_iso(),
        "actor_user_id": user.user_id,
        "reason": req.reason,
    })
    application = await world.upsert_application(application)
    from foundation import DomainEvent
    await governance.emit(DomainEvent(
        event_type=EventType.APPLICATION_STAGE_CHANGED,
        actor=f"user:{user.user_id}",
        subject_type="application",
        subject_id=application.application_id,
        organization_id=user.organization_id,
        payload={"from": previous_name, "to": req.stage_name, "reason": req.reason},
    ))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="application",
        entity_id=application.application_id,
        event_type="application.stage_changed",
        actor_user_id=user.user_id,
        payload={"from": previous_name, "to": req.stage_name, "reason": req.reason},
    ))
    return application.model_dump()


class TalentPoolCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: Optional[str] = Field(default=None, max_length=2000)
    tags: list[str] = Field(default_factory=list, max_length=100)


@app.get("/api/ats/talent-pools")
async def list_ats_talent_pools(user: AppUser = Depends(_current_user)):
    return [pool.model_dump() for pool in await world.list_talent_pools(user.organization_id)]


@app.post("/api/ats/talent-pools")
async def create_ats_talent_pool(req: TalentPoolCreateRequest, user: AppUser = Depends(_current_user)):
    _require_role(user, Role.ADMIN, Role.RECRUITER)
    pool = await world.upsert_talent_pool(TalentPool(
        organization_id=user.organization_id,
        owner_user_id=user.user_id,
        **req.model_dump(),
    ))
    return pool.model_dump()


class TalentPoolMemberRequest(BaseModel):
    candidate_id: str
    note: Optional[str] = Field(default=None, max_length=2000)


@app.get("/api/ats/talent-pools/{talent_pool_id}/members")
async def list_ats_talent_pool_members(talent_pool_id: str, user: AppUser = Depends(_current_user)):
    return [membership.model_dump() for membership in await world.list_talent_pool_members(user.organization_id, talent_pool_id)]


@app.post("/api/ats/talent-pools/{talent_pool_id}/members")
async def add_ats_talent_pool_member(
    talent_pool_id: str, req: TalentPoolMemberRequest, user: AppUser = Depends(_current_user)
):
    _require_role(user, Role.ADMIN, Role.RECRUITER)
    pool_exists = any(pool.talent_pool_id == talent_pool_id for pool in await world.list_talent_pools(user.organization_id))
    if not pool_exists:
        raise HTTPException(status_code=404, detail="Talent pool not found")
    await _scoped_candidate(req.candidate_id, user)
    membership = await world.add_to_talent_pool(TalentPoolMembership(
        organization_id=user.organization_id,
        talent_pool_id=talent_pool_id,
        candidate_id=req.candidate_id,
        added_by_user_id=user.user_id,
        note=req.note,
    ))
    return membership.model_dump()


class ConsentCreateRequest(BaseModel):
    purpose: str = Field(min_length=2, max_length=100)
    legal_basis: Optional[str] = Field(default=None, max_length=200)
    captured_from: str = Field(default="manual", max_length=100)
    evidence_url: Optional[str] = Field(default=None, max_length=2000)
    expires_at: Optional[str] = None


@app.get("/api/ats/candidates/{candidate_id}/consents")
async def list_ats_candidate_consents(candidate_id: str, user: AppUser = Depends(_current_user)):
    await _scoped_candidate(candidate_id, user)
    return [consent.model_dump() for consent in await world.list_candidate_consents(user.organization_id, candidate_id)]


@app.post("/api/ats/candidates/{candidate_id}/consents")
async def create_ats_candidate_consent(
    candidate_id: str, req: ConsentCreateRequest, user: AppUser = Depends(_current_user)
):
    _require_role(user, Role.ADMIN, Role.RECRUITER)
    await _scoped_candidate(candidate_id, user)
    consent = await world.upsert_consent(CandidateConsent(
        organization_id=user.organization_id,
        candidate_id=candidate_id,
        recorded_by_user_id=user.user_id,
        **req.model_dump(),
    ))
    from foundation import DomainEvent
    await governance.emit(DomainEvent(
        event_type=EventType.CONSENT_RECORDED,
        actor=f"user:{user.user_id}",
        subject_type="candidate",
        subject_id=candidate_id,
        organization_id=user.organization_id,
        payload={"purpose": consent.purpose, "status": consent.status.value, "expires_at": consent.expires_at},
    ))
    return consent.model_dump()


class ResumeRecordRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    storage_key: Optional[str] = Field(default=None, max_length=1000)
    storage_url: Optional[str] = Field(default=None, max_length=2000)
    mime_type: Optional[str] = Field(default=None, max_length=160)
    parse_status: str = Field(default="pending", pattern="^(pending|parsed|failed|manual)$")
    parsed_profile: dict[str, Any] = Field(default_factory=dict)
    is_primary: bool = True


@app.get("/api/ats/candidates/{candidate_id}/resumes")
async def list_ats_candidate_resumes(candidate_id: str, user: AppUser = Depends(_current_user)):
    await _scoped_candidate(candidate_id, user)
    return [resume.model_dump() for resume in await world.list_resumes(user.organization_id, candidate_id)]


@app.post("/api/ats/candidates/{candidate_id}/resumes")
async def record_ats_candidate_resume(
    candidate_id: str, req: ResumeRecordRequest, user: AppUser = Depends(_current_user)
):
    _require_role(user, Role.ADMIN, Role.RECRUITER)
    await _scoped_candidate(candidate_id, user)
    resume = await world.upsert_resume(ResumeDocument(
        organization_id=user.organization_id,
        candidate_id=candidate_id,
        uploaded_by_user_id=user.user_id,
        **req.model_dump(),
    ))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="candidate",
        entity_id=candidate_id,
        event_type="resume.recorded",
        actor_user_id=user.user_id,
        payload={"resume_id": resume.resume_id, "parse_status": resume.parse_status},
    ))
    return resume.model_dump()


class InterviewCreateRequest(BaseModel):
    application_id: str
    candidate_id: str
    interview_type: str = Field(default="structured", max_length=100)
    stage_id: Optional[str] = None
    scheduled_at: str = Field(min_length=10, max_length=80)
    duration_minutes: int = Field(default=45, ge=15, le=480)
    timezone: str = Field(default="UTC", min_length=1, max_length=80)
    meeting_url: Optional[str] = Field(default=None, max_length=2000)
    interviewer_ids: list[str] = Field(default_factory=list, max_length=50)


@app.get("/api/ats/interviews")
async def list_ats_interviews(
    application_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
    user: AppUser = Depends(_current_user),
):
    return [interview.model_dump() for interview in await world.list_interviews(
        user.organization_id, application_id=application_id, candidate_id=candidate_id
    )]


@app.post("/api/ats/interviews")
async def create_ats_interview(req: InterviewCreateRequest, user: AppUser = Depends(_current_user)):
    _require_role(user, Role.ADMIN, Role.RECRUITER, Role.HIRING_MANAGER)
    application = await _scoped_application(req.application_id, user)
    await _scoped_candidate(req.candidate_id, user)
    if application.candidate_id != req.candidate_id:
        raise HTTPException(status_code=400, detail="Interview candidate must match its application")
    interview = await world.upsert_interview(Interview(
        organization_id=user.organization_id,
        created_by_user_id=user.user_id,
        **req.model_dump(),
    ))
    from foundation import DomainEvent
    await governance.emit(DomainEvent(
        event_type=EventType.INTERVIEW_SCHEDULED,
        actor=f"user:{user.user_id}",
        subject_type="interview",
        subject_id=interview.interview_id,
        organization_id=user.organization_id,
        payload={"application_id": interview.application_id, "scheduled_at": interview.scheduled_at},
    ))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="candidate",
        entity_id=interview.candidate_id,
        event_type="interview.scheduled",
        actor_user_id=user.user_id,
        payload={"interview_id": interview.interview_id, "application_id": interview.application_id, "scheduled_at": interview.scheduled_at},
    ))
    return interview.model_dump()


class ScorecardCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    requisition_id: Optional[str] = None
    competencies: list[dict[str, Any]] = Field(default_factory=list, max_length=50)


@app.get("/api/ats/scorecards")
async def list_ats_scorecards(requisition_id: Optional[str] = None, user: AppUser = Depends(_current_user)):
    return [scorecard.model_dump() for scorecard in await world.list_scorecards(user.organization_id, requisition_id)]


@app.post("/api/ats/scorecards")
async def create_ats_scorecard(req: ScorecardCreateRequest, user: AppUser = Depends(_current_user)):
    _require_role(user, Role.ADMIN, Role.RECRUITER, Role.HIRING_MANAGER)
    if req.requisition_id:
        await _scoped_requisition(req.requisition_id, user)
    scorecard = await world.upsert_scorecard(Scorecard(
        organization_id=user.organization_id,
        created_by_user_id=user.user_id,
        **req.model_dump(),
    ))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="requisition" if scorecard.requisition_id else "scorecard",
        entity_id=scorecard.requisition_id or scorecard.scorecard_id,
        event_type="scorecard.created",
        actor_user_id=user.user_id,
        payload={"scorecard_id": scorecard.scorecard_id, "competency_count": len(scorecard.competencies)},
    ))
    return scorecard.model_dump()


class InterviewFeedbackCreateRequest(BaseModel):
    scorecard_id: Optional[str] = None
    recommendation: str = Field(pattern="^(strong_yes|yes|no|strong_no|abstain)$")
    ratings: dict[str, float] = Field(default_factory=dict)
    strengths: list[str] = Field(default_factory=list, max_length=100)
    concerns: list[str] = Field(default_factory=list, max_length=100)
    summary: Optional[str] = Field(default=None, max_length=10000)


class CollaborationMentionCreateRequest(BaseModel):
    mentioned_user_id: str = Field(min_length=3, max_length=200)
    feedback_id: Optional[str] = Field(default=None, max_length=200)
    context: Optional[str] = Field(default=None, max_length=2000)


class CandidateCommunicationCreateRequest(BaseModel):
    direction: str = Field(pattern="^(inbound|outbound)$")
    channel: str = Field(pattern="^(email|phone|sms|in_app|other)$")
    subject: Optional[str] = Field(default=None, max_length=500)
    body: Optional[str] = Field(default=None, max_length=10000)


class HiringDecisionCreateRequest(BaseModel):
    application_id: str = Field(min_length=3, max_length=200)
    outcome: str = Field(pattern="^(hire|reject)$")
    rationale: str = Field(min_length=10, max_length=10_000)


def _has_active_recruiting_consent(consents: list[CandidateConsent]) -> Optional[CandidateConsent]:
    now = utcnow_iso()
    for consent in consents:
        status = getattr(consent.status, "value", consent.status)
        if (
            status == "granted"
            and consent.purpose in {"recruiting", "data_processing"}
            and (not consent.expires_at or consent.expires_at > now)
        ):
            return consent
    return None


@app.get("/api/ats/interviews/{interview_id}/feedback")
async def list_ats_interview_feedback(interview_id: str, user: AppUser = Depends(_current_user)):
    if not await world.get_interview(user.organization_id, interview_id):
        raise HTTPException(status_code=404, detail="Interview not found")
    return [feedback.model_dump() for feedback in await world.list_interview_feedback(user.organization_id, interview_id)]


@app.post("/api/ats/interviews/{interview_id}/feedback")
async def create_ats_interview_feedback(
    interview_id: str, req: InterviewFeedbackCreateRequest, user: AppUser = Depends(_current_user)
):
    _require_role(user, Role.ADMIN, Role.RECRUITER, Role.HIRING_MANAGER)
    interview = await world.get_interview(user.organization_id, interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    if req.scorecard_id and not await world.get_scorecard(user.organization_id, req.scorecard_id):
        raise HTTPException(status_code=404, detail="Scorecard not found")
    feedback = await world.upsert_interview_feedback(InterviewFeedback(
        organization_id=user.organization_id,
        interview_id=interview_id,
        interviewer_id=user.user_id,
        **req.model_dump(),
    ))
    from foundation import DomainEvent
    await governance.emit(DomainEvent(
        event_type=EventType.SCORECARD_SUBMITTED,
        actor=f"user:{user.user_id}",
        subject_type="interview",
        subject_id=interview_id,
        organization_id=user.organization_id,
        payload={"feedback_id": feedback.feedback_id, "recommendation": feedback.recommendation},
    ))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="candidate",
        entity_id=interview.candidate_id,
        event_type="interview.feedback_submitted",
        actor_user_id=user.user_id,
        payload={
            "interview_id": interview_id,
            "feedback_id": feedback.feedback_id,
            "scorecard_id": feedback.scorecard_id,
            "recommendation": feedback.recommendation,
        },
    ))
    return feedback.model_dump()


@app.get("/api/ats/candidates/{candidate_id}/collaboration/mentions")
async def list_ats_candidate_mentions(candidate_id: str, user: AppUser = Depends(_current_user)):
    _require_role(user, Role.ADMIN, Role.RECRUITER, Role.HIRING_MANAGER)
    await _scoped_candidate(candidate_id, user)
    return [mention.model_dump() for mention in await world.list_collaboration_mentions(user.organization_id, candidate_id)]


@app.post("/api/ats/candidates/{candidate_id}/collaboration/mentions")
async def create_ats_candidate_mention(
    candidate_id: str, req: CollaborationMentionCreateRequest, user: AppUser = Depends(_current_user)
):
    _require_role(user, Role.ADMIN, Role.RECRUITER, Role.HIRING_MANAGER)
    await _scoped_candidate(candidate_id, user)
    mentioned_user = await db.users.find_one(
        {"user_id": req.mentioned_user_id, "organization_id": user.organization_id}, {"_id": 0}
    )
    if not mentioned_user:
        raise HTTPException(status_code=404, detail="Mentioned user not found in this organization")
    if req.feedback_id:
        feedback = await world.get_interview_feedback(user.organization_id, req.feedback_id)
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")
        interview = await world.get_interview(user.organization_id, feedback.interview_id)
        if not interview or interview.candidate_id != candidate_id:
            raise HTTPException(status_code=400, detail="Feedback does not belong to this candidate")
    mention = await world.record_collaboration_mention(CollaborationMention(
        organization_id=user.organization_id,
        candidate_id=candidate_id,
        mentioned_user_id=req.mentioned_user_id,
        mentioned_by_user_id=user.user_id,
        feedback_id=req.feedback_id,
        context=req.context,
    ))
    await governance.emit(DomainEvent(
        event_type=EventType.COLLABORATION_MENTION_CREATED,
        actor=f"user:{user.user_id}",
        subject_type="candidate",
        subject_id=candidate_id,
        organization_id=user.organization_id,
        payload={"mention_id": mention.mention_id, "mentioned_user_id": mention.mentioned_user_id, "feedback_id": mention.feedback_id},
    ))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="candidate",
        entity_id=candidate_id,
        event_type="collaboration.mention_created",
        actor_user_id=user.user_id,
        payload={"mention_id": mention.mention_id, "mentioned_user_id": mention.mentioned_user_id, "feedback_id": mention.feedback_id},
    ))
    return mention.model_dump()


@app.get("/api/ats/candidates/{candidate_id}/communications")
async def list_ats_candidate_communications(candidate_id: str, user: AppUser = Depends(_current_user)):
    _require_role(user, Role.ADMIN, Role.RECRUITER, Role.HIRING_MANAGER)
    await _scoped_candidate(candidate_id, user)
    return [communication.model_dump() for communication in await world.list_candidate_communications(user.organization_id, candidate_id)]


@app.post("/api/ats/candidates/{candidate_id}/communications")
async def record_ats_candidate_communication(
    candidate_id: str, req: CandidateCommunicationCreateRequest, user: AppUser = Depends(_current_user)
):
    _require_role(user, Role.ADMIN, Role.RECRUITER)
    await _scoped_candidate(candidate_id, user)
    consent = None
    if req.direction == "outbound" and req.channel in {"email", "sms"}:
        consent = _has_active_recruiting_consent(
            await world.list_candidate_consents(user.organization_id, candidate_id)
        )
        if not consent:
            raise HTTPException(status_code=409, detail="Active recruiting consent is required before recording outbound email or SMS")
    communication = await world.record_candidate_communication(CandidateCommunication(
        organization_id=user.organization_id,
        candidate_id=candidate_id,
        direction=req.direction,
        channel=req.channel,
        subject=req.subject,
        body=req.body,
        consent_id=consent.consent_id if consent else None,
        recorded_by_user_id=user.user_id,
    ))
    await governance.emit(DomainEvent(
        event_type=EventType.CANDIDATE_COMMUNICATION_RECORDED,
        actor=f"user:{user.user_id}",
        subject_type="candidate",
        subject_id=candidate_id,
        organization_id=user.organization_id,
        payload={"communication_id": communication.communication_id, "direction": communication.direction, "channel": communication.channel, "delivery_state": communication.delivery_state},
    ))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="candidate",
        entity_id=candidate_id,
        event_type="candidate.communication_recorded",
        actor_user_id=user.user_id,
        payload={"communication_id": communication.communication_id, "direction": communication.direction, "channel": communication.channel, "consent_id": communication.consent_id},
    ))
    return communication.model_dump()


@app.get("/api/ats/hiring-decisions")
async def list_ats_hiring_decisions(
    application_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
    user: AppUser = Depends(_current_user),
):
    _require_role(user, Role.ADMIN, Role.RECRUITER, Role.HIRING_MANAGER)
    return [decision.model_dump() for decision in await world.list_hiring_decisions(
        user.organization_id, application_id=application_id, candidate_id=candidate_id
    )]


@app.post("/api/ats/hiring-decisions")
async def request_ats_hiring_decision(
    req: HiringDecisionCreateRequest, user: AppUser = Depends(_current_user)
):
    _require_role(user, Role.ADMIN, Role.RECRUITER, Role.HIRING_MANAGER)
    application = await _scoped_application(req.application_id, user)
    application_status = getattr(application.status, "value", application.status)
    if application_status != "active":
        raise HTTPException(status_code=409, detail="Only an active application can enter final hiring-decision review")
    existing = await world.list_hiring_decisions(user.organization_id, application_id=application.application_id)
    if any(item.status == "awaiting_approval" for item in existing):
        raise HTTPException(status_code=409, detail="A hiring decision is already awaiting approval for this application")
    decision = HiringDecision(
        organization_id=user.organization_id,
        application_id=application.application_id,
        candidate_id=application.candidate_id,
        requisition_id=application.requisition_id,
        outcome=req.outcome,
        rationale=req.rationale,
        requested_by_user_id=user.user_id,
    )
    approval = Approval(
        organization_id=user.organization_id,
        subject_type="hiring_decision",
        subject_id=decision.hiring_decision_id,
        requested_by=user.user_id,
        reason=f"Approve final {decision.outcome} decision for application {application.application_id}",
        context={
            "hiring_decision_id": decision.hiring_decision_id,
            "application_id": application.application_id,
            "candidate_id": application.candidate_id,
            "outcome": decision.outcome,
            "correlation_id": decision.hiring_decision_id,
        },
    )
    decision.approval_id = approval.approval_id
    await world.create_hiring_decision(decision)
    await governance.request_approval(approval)
    await governance.emit(DomainEvent(
        event_type=EventType.HIRING_DECISION_REQUESTED,
        actor=f"user:{user.user_id}",
        subject_type="hiring_decision",
        subject_id=decision.hiring_decision_id,
        organization_id=user.organization_id,
        payload={"application_id": application.application_id, "candidate_id": application.candidate_id, "outcome": decision.outcome, "approval_id": approval.approval_id},
        correlation_id=decision.hiring_decision_id,
    ))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="candidate",
        entity_id=application.candidate_id,
        event_type="hiring_decision.requested",
        actor_user_id=user.user_id,
        payload={"hiring_decision_id": decision.hiring_decision_id, "application_id": application.application_id, "outcome": decision.outcome, "approval_id": approval.approval_id},
    ))
    response = decision.model_dump()
    response["approval"] = approval.model_dump()
    return response


@app.get("/api/ats/activity/{entity_type}/{entity_id}")
async def list_ats_activity(entity_type: str, entity_id: str, user: AppUser = Depends(_current_user)):
    return [activity.model_dump() for activity in await world.list_activity(user.organization_id, entity_type, entity_id)]


@app.get("/api/ats/onboarding-handoffs")
async def list_ats_onboarding_handoffs(user: AppUser = Depends(_current_user)):
    return [handoff.model_dump() for handoff in await world.list_onboarding_handoffs(user.organization_id)]


@app.post("/api/ats/onboarding-handoffs")
async def create_ats_onboarding_handoff(
    req: OnboardingHandoffCreateRequest, user: AppUser = Depends(_current_user)
):
    _require_role(user, Role.ADMIN, Role.RECRUITER)
    await _scoped_candidate(req.candidate_id, user)
    await _scoped_job(req.job_id, user)
    if req.application_id:
        application = await _scoped_application(req.application_id, user)
        if application.candidate_id != req.candidate_id or application.job_id != req.job_id:
            raise HTTPException(status_code=400, detail="Application does not match the candidate and job")
    offer = await world.get_offer(user.organization_id, req.offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if offer.status.value != "accepted":
        raise HTTPException(status_code=400, detail="Only an accepted offer can be handed off")
    if offer.candidate_id != req.candidate_id or offer.job_id != req.job_id:
        raise HTTPException(status_code=400, detail="Offer does not match the candidate and job")

    handoff = await world.upsert_onboarding_handoff(OnboardingHandoff(
        organization_id=user.organization_id,
        offer_id=req.offer_id,
        candidate_id=req.candidate_id,
        job_id=req.job_id,
        application_id=req.application_id,
        target_start_date=req.target_start_date,
        owner_user_id=req.owner_user_id,
        destination_system=req.destination_system,
        checklist=req.checklist,
    ))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="onboarding_handoff",
        entity_id=handoff.onboarding_handoff_id,
        event_type="onboarding_handoff.created",
        actor_user_id=user.user_id,
        payload={"offer_id": handoff.offer_id, "destination_system": handoff.destination_system},
    ))
    from foundation import DomainEvent
    await governance.emit(DomainEvent(
        event_type=EventType.ONBOARDING_HANDOFF_CREATED,
        actor=f"user:{user.user_id}",
        subject_type="onboarding_handoff",
        subject_id=handoff.onboarding_handoff_id,
        organization_id=user.organization_id,
        payload={"offer_id": handoff.offer_id, "candidate_id": handoff.candidate_id, "job_id": handoff.job_id},
    ))
    return handoff.model_dump()


# ============================================================
#   INTELLIGENCE — recommendations (never execute)
# ============================================================

@app.get("/api/intelligence/hiring/{job_id}")
async def hiring_recs(job_id: str, top_n: int = 5, user: AppUser = Depends(_current_user)):
    await _scoped_job(job_id, user)
    recs = await hiring_recommendations_for_job(world, user.organization_id, job_id, top_n=top_n)
    return {"job_id": job_id, "recommendations": [r.model_dump() for r in recs]}


@app.get("/api/intelligence/offer/{candidate_id}")
async def offer_rec(candidate_id: str, user: AppUser = Depends(_current_user)):
    await _scoped_candidate(candidate_id, user)
    r = await offer_recommendation(world, user.organization_id, candidate_id)
    if not r:
        raise HTTPException(404, "candidate not found")
    return r.model_dump()


@app.get("/api/intelligence/organization/health")
async def org_health(user: AppUser = Depends(_current_user)):
    return await organizational_health(world, user.organization_id)


@app.get("/api/intelligence/workforce/skill-gaps")
async def skill_gaps(user: AppUser = Depends(_current_user)):
    return await skill_gap_analysis(world, user.organization_id)


@app.get("/api/intelligence/strategy")
async def strategy(user: AppUser = Depends(_current_user)):
    r = await hiring_strategy(world, user.organization_id)
    return r.model_dump()


# ============================================================
#   PLANNER — propose plans (do NOT execute)
# ============================================================

class PlanRequest(BaseModel):
    goal: str = Field(min_length=3, max_length=2000)
    context: dict[str, Any] = Field(default_factory=dict)


@app.post("/api/planner/plan")
async def make_plan(req: PlanRequest, user: AppUser = Depends(_current_user)):
    plan = await planner.plan(req.goal, user.organization_id, req.context)
    return plan.model_dump()


# ============================================================
#   CAPABILITY REGISTRY
# ============================================================

@app.get("/api/platform/capabilities")
async def list_capabilities(user: AppUser = Depends(_current_user)):
    return [s.model_dump() for s in capability_registry.list_specs()]


# ============================================================
#   POLICY
# ============================================================

@app.get("/api/platform/policies")
async def list_policies(user: AppUser = Depends(_current_user)):
    return [p.model_dump() for p in await policy_engine.list_policies(user.organization_id)]


# ============================================================
#   RUNTIME — the ONLY layer that executes business actions
# ============================================================

class ExecuteRequest(BaseModel):
    goal: str = Field(min_length=3, max_length=2000)
    steps: list[dict[str, Any]] = Field(min_length=1, max_length=20)
    decision_id: Optional[str] = None


RETENTION_EXECUTION_CAPABILITIES = {
    "cap.execute_retention_archive",
    "cap.execute_retention_erasure",
}


async def _record_completed_retention_events(result: ExecutionRecord, actor_user_id: str) -> None:
    """Emit retention completion records for any terminal runtime path, including resume."""
    if result.status != ExecutionStatus.SUCCEEDED:
        return
    for step_result in result.step_results:
        capability_id = step_result.get("capability_id")
        output = step_result.get("output") or {}
        if not step_result.get("ok") or capability_id not in RETENTION_EXECUTION_CAPABILITIES:
            continue
        event_type = (
            EventType.RETENTION_ARCHIVE_COMPLETED
            if capability_id == "cap.execute_retention_archive"
            else EventType.RETENTION_ERASURE_COMPLETED
        )
        await governance.emit(DomainEvent(
            event_type=event_type,
            actor=actor_user_id,
            subject_type=output.get("subject_type", "retention_subject"),
            subject_id=output.get("subject_id", output.get("retention_case_id", "unknown")),
            organization_id=result.organization_id,
            payload={
                "retention_case_id": output.get("retention_case_id"),
                "action": output.get("action"),
                "execution_id": result.execution_id,
                "redaction_scope": "direct operational profile and application-evaluation data"
                if capability_id == "cap.execute_retention_erasure" else None,
            },
            correlation_id=result.correlation_id,
        ))

@app.post("/api/runtime/execute")
async def execute_plan(req: ExecuteRequest, user: AppUser = Depends(_current_user)):
    if any(step.get("capability_id") in RETENTION_EXECUTION_CAPABILITIES for step in req.steps):
        _require_role(user, Role.ADMIN)
    ex = ExecutionRecord(
        organization_id=user.organization_id,
        user_id=user.user_id,
        user_role=user.role,
        goal=req.goal,
        steps=[PlanStep(
            capability_id=s["capability_id"],
            inputs=s.get("inputs", {}),
            description=s.get("description"),
            confidence=float(s.get("confidence", 0.7)),
            sensitivity=Sensitivity(s.get("sensitivity", "internal")),
        ) for s in req.steps],
        correlation_id=new_execution_id(),
        decision_id=req.decision_id,
    )
    result = await runtime.execute(ex)

    await _record_completed_retention_events(result, user.user_id)

    # Automatic reflection when terminal
    if result.status in (ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED,
                         ExecutionStatus.POLICY_BLOCKED):
        report = await reflection.summarize_execution(result.model_dump())
        await reflection.record(report)

    return result.model_dump()


@app.get("/api/runtime/executions")
async def list_executions(user: AppUser = Depends(_current_user)):
    execs = await runtime.list_executions(user.organization_id)
    return [e.model_dump() for e in execs]


@app.get("/api/runtime/executions/{execution_id}")
async def get_execution(execution_id: str, user: AppUser = Depends(_current_user)):
    ex = await runtime.get_execution(execution_id)
    if not ex or ex.organization_id != user.organization_id:
        raise HTTPException(404, "execution not found")
    return ex.model_dump()


# ============================================================
#   GOVERNANCE — audit + approvals
# ============================================================

@app.get("/api/governance/events")
async def list_events(
    event_type: Optional[str] = None,
    subject_id: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    user: AppUser = Depends(_current_user),
):
    events = await governance.list_events(
        organization_id=user.organization_id,
        event_type=event_type,
        subject_id=subject_id,
        limit=limit,
    )
    return [e.model_dump() for e in events]


@app.get("/api/governance/events/replay/{correlation_id}")
async def replay_events(correlation_id: str, user: AppUser = Depends(_current_user)):
    events = await governance.replay(correlation_id)
    if any(event.organization_id != user.organization_id for event in events):
        raise HTTPException(status_code=404, detail="Event trace not found")
    return [e.model_dump() for e in events]


@app.get("/api/governance/approvals")
async def list_approvals(
    status: Optional[str] = None,
    user: AppUser = Depends(_current_user),
):
    approvals = await governance.list_approvals(user.organization_id, status=status)
    return [a.model_dump() for a in approvals]


class DecideApprovalRequest(BaseModel):
    decision: str  # granted | denied
    note: Optional[str] = None


@app.post("/api/governance/approvals/{approval_id}/decide")
async def decide_approval(
    approval_id: str,
    req: DecideApprovalRequest,
    user: AppUser = Depends(_current_user),
):
    _require_role(user, Role.ADMIN, Role.EXECUTIVE, Role.HIRING_MANAGER)
    if req.decision not in ("granted", "denied"):
        raise HTTPException(400, "decision must be 'granted' or 'denied'")
    approvals = await governance.list_approvals(user.organization_id)
    approval = next((item for item in approvals if item.approval_id == approval_id), None)
    if not approval:
        raise HTTPException(404, "approval not found")
    if getattr(approval, "status", None) != "pending":
        raise HTTPException(status_code=409, detail="This approval has already been decided")
    if getattr(approval, "subject_type", None) == "hiring_decision" and getattr(approval, "requested_by", None) == user.user_id:
        raise HTTPException(status_code=403, detail="A requester cannot approve or deny their own hiring decision")
    if getattr(approval, "subject_type", None) == "hiring_decision" and req.decision == "granted":
        decision = await world.get_hiring_decision(user.organization_id, approval.subject_id)
        if not decision or decision.approval_id != approval.approval_id:
            raise HTTPException(404, "hiring decision not found")
        application = await world.get_application(user.organization_id, decision.application_id)
        if not application or getattr(application.status, "value", application.status) != "active":
            raise HTTPException(status_code=409, detail="The target application is no longer active; hiring decision approval cannot proceed")
    if approval.context.get("capability_id") in RETENTION_EXECUTION_CAPABILITIES:
        _require_role(user, Role.ADMIN)
    a = await governance.decide_approval(approval_id, req.decision, user.user_id, req.note)
    if not a:
        raise HTTPException(404, "approval not found")
    response = a.model_dump()
    if (
        a.status == "granted"
        and a.context.get("capability_id") in RETENTION_EXECUTION_CAPABILITIES
        and a.context.get("execution_id")
    ):
        resumed = await runtime.resume_after_approval(a.context["execution_id"], user.organization_id)
        await _record_completed_retention_events(resumed, user.user_id)
        response["resumed_execution"] = resumed.model_dump()
    if getattr(a, "subject_type", None) == "hiring_decision":
        decision = await world.get_hiring_decision(user.organization_id, a.subject_id)
        if not decision or decision.approval_id != a.approval_id:
            raise HTTPException(404, "hiring decision not found")
        application = None
        if a.status == "granted":
            application = await world.apply_hiring_decision_application_status(user.organization_id, decision)
            if not application:
                response["hiring_decision"] = decision.model_dump()
                response["hiring_decision_error"] = "The application changed during approval. The decision remains awaiting approval and no final outcome was applied."
                return response
        resolution_status = "effective" if a.status == "granted" else "denied"
        resolved = await world.resolve_hiring_decision(
            user.organization_id,
            decision.hiring_decision_id,
            approval_id=a.approval_id,
            status=resolution_status,
            resolved_by_user_id=user.user_id,
        )
        if not resolved:
            raise HTTPException(404, "hiring decision not found")
        await governance.emit(DomainEvent(
            event_type=EventType.HIRING_DECISION_EFFECTIVE if a.status == "granted" else EventType.HIRING_DECISION_DENIED,
            actor=f"user:{user.user_id}",
            subject_type="hiring_decision",
            subject_id=resolved.hiring_decision_id,
            organization_id=user.organization_id,
            payload={"approval_id": a.approval_id, "application_id": resolved.application_id, "outcome": resolved.outcome, "application_status": getattr(application.status, "value", application.status) if application else None},
            correlation_id=resolved.hiring_decision_id,
        ))
        await world.record_activity(ActivityRecord(
            organization_id=user.organization_id,
            entity_type="candidate",
            entity_id=resolved.candidate_id,
            event_type="hiring_decision.effective" if a.status == "granted" else "hiring_decision.denied",
            actor_user_id=user.user_id,
            payload={"hiring_decision_id": resolved.hiring_decision_id, "approval_id": a.approval_id, "outcome": resolved.outcome, "application_id": resolved.application_id},
        ))
        response["hiring_decision"] = resolved.model_dump()
    return response


# ============================================================
#   ENTERPRISE CONTROLS — retention, audit export, readiness
# ============================================================

class CreateDataSubjectRequestRequest(BaseModel):
    candidate_id: str = Field(min_length=3, max_length=128)
    request_type: str = Field(pattern="^(access|correction|erasure)$")
    request_summary: str = Field(min_length=10, max_length=4_000)
    intake_channel: str = Field(default="staff_recorded", min_length=2, max_length=100)


class DecideDataSubjectRequestRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected|on_hold)$")
    note: Optional[str] = Field(default=None, max_length=2_000)


@app.get("/api/enterprise/data-subject-requests")
async def list_data_subject_requests(
    status: Optional[str] = None, user: AppUser = Depends(_current_user)
):
    _require_role(user, Role.ADMIN)
    try:
        parsed_status = DataSubjectRequestStatus(status) if status else None
    except ValueError as exc:
        raise HTTPException(400, "invalid data-subject request status") from exc
    requests = await world.list_data_subject_requests(user.organization_id, parsed_status)
    return [request.model_dump() for request in requests]


@app.post("/api/enterprise/data-subject-requests")
async def create_data_subject_request(
    req: CreateDataSubjectRequestRequest, user: AppUser = Depends(_current_user)
):
    _require_role(user, Role.ADMIN, Role.RECRUITER)
    await _scoped_candidate(req.candidate_id, user)
    request = await world.create_data_subject_request(DataSubjectRequest(
        organization_id=user.organization_id,
        candidate_id=req.candidate_id,
        request_type=req.request_type,
        request_summary=req.request_summary,
        intake_channel=req.intake_channel,
        requested_by_user_id=user.user_id,
    ))
    await governance.emit(DomainEvent(
        event_type=EventType.DATA_SUBJECT_REQUESTED,
        actor=f"user:{user.user_id}",
        subject_type="candidate",
        subject_id=request.candidate_id,
        organization_id=user.organization_id,
        payload={"data_subject_request_id": request.data_subject_request_id, "request_type": request.request_type, "intake_channel": request.intake_channel},
        correlation_id=request.data_subject_request_id,
    ))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="candidate",
        entity_id=request.candidate_id,
        event_type="data_subject_request.requested",
        actor_user_id=user.user_id,
        payload={"data_subject_request_id": request.data_subject_request_id, "request_type": request.request_type},
        correlation_id=request.data_subject_request_id,
    ))
    return request.model_dump()


@app.post("/api/enterprise/data-subject-requests/{data_subject_request_id}/decide")
async def decide_data_subject_request(
    data_subject_request_id: str,
    req: DecideDataSubjectRequestRequest,
    user: AppUser = Depends(_current_user),
):
    _require_role(user, Role.ADMIN)
    existing = await world.get_data_subject_request(user.organization_id, data_subject_request_id)
    if not existing:
        raise HTTPException(404, "data-subject request not found")
    if existing.status != DataSubjectRequestStatus.PENDING_REVIEW:
        raise HTTPException(409, "data-subject request has already been reviewed")
    decision = DataSubjectRequestStatus(req.decision)
    request = await world.decide_data_subject_request(
        user.organization_id,
        data_subject_request_id,
        status=decision,
        reviewed_by_user_id=user.user_id,
        review_note=req.note,
    )
    if not request:
        raise HTTPException(409, "data-subject request could not be reviewed")

    if request.status == DataSubjectRequestStatus.APPROVED and request.request_type == "erasure":
        retention_case = await world.create_retention_case(RetentionCase(
            organization_id=user.organization_id,
            subject_type="candidate",
            subject_id=request.candidate_id,
            requested_action="erase",
            reason=f"Approved data-subject erasure request {request.data_subject_request_id}: {request.request_summary}",
            requested_by_user_id=user.user_id,
        ))
        request = await world.link_data_subject_request_artifact(
            user.organization_id,
            request.data_subject_request_id,
            retention_case_id=retention_case.retention_case_id,
        ) or request
    if request.status == DataSubjectRequestStatus.APPROVED and request.request_type == "access":
        events = await governance.list_events(
            organization_id=user.organization_id, subject_id=request.candidate_id, limit=500
        )
        manifest = await world.create_audit_export_manifest(AuditExportManifest(
            organization_id=user.organization_id,
            requested_by_user_id=user.user_id,
            filters={"kind": "data_subject_access", "candidate_id": request.candidate_id, "limit": 500},
            event_count=len(events),
            status=AuditExportStatus.READY,
        ))
        request = await world.link_data_subject_request_artifact(
            user.organization_id,
            request.data_subject_request_id,
            audit_export_id=manifest.audit_export_id,
        ) or request

    await governance.emit(DomainEvent(
        event_type=EventType.DATA_SUBJECT_REQUEST_DECIDED,
        actor=f"user:{user.user_id}",
        subject_type="candidate",
        subject_id=request.candidate_id,
        organization_id=user.organization_id,
        payload={"data_subject_request_id": request.data_subject_request_id, "request_type": request.request_type, "decision": request.status.value, "retention_case_id": request.retention_case_id, "audit_export_id": request.audit_export_id},
        correlation_id=request.data_subject_request_id,
    ))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="candidate",
        entity_id=request.candidate_id,
        event_type="data_subject_request.decided",
        actor_user_id=user.user_id,
        payload={"data_subject_request_id": request.data_subject_request_id, "decision": request.status.value, "request_type": request.request_type},
        correlation_id=request.data_subject_request_id,
    ))
    return request.model_dump()


@app.post("/api/enterprise/data-subject-requests/{data_subject_request_id}/fulfill")
async def fulfill_data_subject_request(
    data_subject_request_id: str, user: AppUser = Depends(_current_user)
):
    _require_role(user, Role.ADMIN)
    request = await world.get_data_subject_request(user.organization_id, data_subject_request_id)
    if not request:
        raise HTTPException(404, "data-subject request not found")
    if request.status != DataSubjectRequestStatus.APPROVED:
        raise HTTPException(409, "data-subject request requires approved review before fulfillment")
    if request.request_type == "erasure":
        if not request.retention_case_id:
            raise HTTPException(409, "approved erasure request requires a linked retention case")
        retention_case = await world.get_retention_case(user.organization_id, request.retention_case_id)
        if not retention_case or retention_case.status != RetentionCaseStatus.COMPLETED:
            raise HTTPException(409, "erasure fulfillment requires completed policy-gated retention execution")
    fulfilled = await world.fulfill_data_subject_request(
        user.organization_id, data_subject_request_id, fulfilled_by_user_id=user.user_id
    )
    if not fulfilled:
        raise HTTPException(409, "data-subject request could not be fulfilled")
    await governance.emit(DomainEvent(
        event_type=EventType.DATA_SUBJECT_REQUEST_FULFILLED,
        actor=f"user:{user.user_id}",
        subject_type="candidate",
        subject_id=fulfilled.candidate_id,
        organization_id=user.organization_id,
        payload={"data_subject_request_id": fulfilled.data_subject_request_id, "request_type": fulfilled.request_type, "retention_case_id": fulfilled.retention_case_id, "audit_export_id": fulfilled.audit_export_id},
        correlation_id=fulfilled.data_subject_request_id,
    ))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="candidate",
        entity_id=fulfilled.candidate_id,
        event_type="data_subject_request.fulfilled",
        actor_user_id=user.user_id,
        payload={"data_subject_request_id": fulfilled.data_subject_request_id, "request_type": fulfilled.request_type},
        correlation_id=fulfilled.data_subject_request_id,
    ))
    return fulfilled.model_dump()

class CreateRetentionCaseRequest(BaseModel):
    subject_type: str
    subject_id: str = Field(min_length=3, max_length=128)
    requested_action: str
    reason: str = Field(min_length=10, max_length=2_000)
    legal_hold: bool = False


class DecideRetentionCaseRequest(BaseModel):
    decision: str
    note: Optional[str] = Field(default=None, max_length=2_000)


def _retention_subject_is_supported(subject_type: str) -> bool:
    return subject_type in {"candidate", "application"}


async def _retention_subject_exists(subject_type: str, subject_id: str, user: AppUser) -> bool:
    if subject_type == "candidate":
        return await world.get_candidate_for_organization(user.organization_id, subject_id) is not None
    if subject_type == "application":
        return await world.get_application(user.organization_id, subject_id) is not None
    return False


@app.get("/api/enterprise/retention-cases")
async def list_retention_cases(
    status: Optional[str] = None,
    user: AppUser = Depends(_current_user),
):
    _require_role(user, Role.ADMIN)
    try:
        parsed_status = RetentionCaseStatus(status) if status else None
    except ValueError as exc:
        raise HTTPException(400, "invalid retention status") from exc
    cases = await world.list_retention_cases(user.organization_id, parsed_status)
    return [retention_case.model_dump() for retention_case in cases]


@app.post("/api/enterprise/retention-cases")
async def create_retention_case(req: CreateRetentionCaseRequest, user: AppUser = Depends(_current_user)):
    _require_role(user, Role.ADMIN)
    if req.requested_action not in {"archive", "erase"}:
        raise HTTPException(400, "requested_action must be 'archive' or 'erase'")
    if not _retention_subject_is_supported(req.subject_type):
        raise HTTPException(400, "retention review currently supports candidate and application subjects")
    if not await _retention_subject_exists(req.subject_type, req.subject_id, user):
        raise HTTPException(404, "retention subject not found")
    retention_case = await world.create_retention_case(RetentionCase(
        organization_id=user.organization_id,
        subject_type=req.subject_type,
        subject_id=req.subject_id,
        requested_action=req.requested_action,
        reason=req.reason,
        requested_by_user_id=user.user_id,
        legal_hold=req.legal_hold,
    ))
    await governance.emit(DomainEvent(
        event_type=EventType.RETENTION_CASE_REQUESTED,
        actor=user.user_id,
        subject_type=req.subject_type,
        subject_id=req.subject_id,
        organization_id=user.organization_id,
        payload={"retention_case_id": retention_case.retention_case_id, "requested_action": req.requested_action, "legal_hold": req.legal_hold},
    ))
    return retention_case.model_dump()


@app.post("/api/enterprise/retention-cases/{retention_case_id}/decide")
async def decide_retention_case(
    retention_case_id: str,
    req: DecideRetentionCaseRequest,
    user: AppUser = Depends(_current_user),
):
    _require_role(user, Role.ADMIN)
    allowed = {
        RetentionCaseStatus.ON_HOLD,
        RetentionCaseStatus.APPROVED_FOR_ARCHIVE,
        RetentionCaseStatus.APPROVED_FOR_ERASURE,
        RetentionCaseStatus.REJECTED,
    }
    try:
        decision = RetentionCaseStatus(req.decision)
    except ValueError as exc:
        raise HTTPException(400, "invalid retention decision") from exc
    if decision not in allowed:
        raise HTTPException(400, "decision must be a review outcome")
    retention_case = await world.decide_retention_case(
        user.organization_id,
        retention_case_id,
        status=decision,
        reviewed_by_user_id=user.user_id,
        decision_note=req.note,
    )
    if not retention_case:
        raise HTTPException(404, "retention case not found")
    await governance.emit(DomainEvent(
        event_type=EventType.RETENTION_CASE_DECIDED,
        actor=user.user_id,
        subject_type=retention_case.subject_type,
        subject_id=retention_case.subject_id,
        organization_id=user.organization_id,
        payload={"retention_case_id": retention_case.retention_case_id, "decision": decision.value, "destructive_action_executed": False},
    ))
    return retention_case.model_dump()


@app.post("/api/enterprise/retention-cases/{retention_case_id}/execute")
async def execute_retention_case(
    retention_case_id: str,
    user: AppUser = Depends(_current_user),
):
    """Trigger a separately policy-evaluated retention action after an administrator review."""
    _require_role(user, Role.ADMIN)
    retention_case = await world.get_retention_case(user.organization_id, retention_case_id)
    if not retention_case:
        raise HTTPException(404, "retention case not found")
    if retention_case.legal_hold:
        raise HTTPException(409, "retention action is blocked by legal hold")
    required_capability = {
        RetentionCaseStatus.APPROVED_FOR_ARCHIVE: "cap.execute_retention_archive",
        RetentionCaseStatus.APPROVED_FOR_ERASURE: "cap.execute_retention_erasure",
    }.get(retention_case.status)
    if not required_capability:
        raise HTTPException(409, "retention case requires an approved archive or erasure decision")
    return await execute_plan(ExecuteRequest(
        goal=f"Execute approved retention {retention_case.requested_action} for {retention_case.subject_type}",
        steps=[{
            "capability_id": required_capability,
            "inputs": {"retention_case_id": retention_case.retention_case_id},
            "description": "Policy-gated retention execution after approved review",
            "confidence": 1.0,
            "sensitivity": "restricted",
        }],
    ), user)


@app.post("/api/enterprise/audit-exports")
async def request_audit_export(
    event_type: Optional[str] = Query(default=None, max_length=160),
    subject_id: Optional[str] = Query(default=None, max_length=160),
    user: AppUser = Depends(_current_user),
):
    _require_role(user, Role.ADMIN)
    events = await governance.list_events(
        organization_id=user.organization_id, event_type=event_type, subject_id=subject_id, limit=500
    )
    manifest = await world.create_audit_export_manifest(AuditExportManifest(
        organization_id=user.organization_id,
        requested_by_user_id=user.user_id,
        filters={"event_type": event_type, "subject_id": subject_id, "limit": 500},
        event_count=len(events),
        status=AuditExportStatus.READY,
    ))
    await governance.emit(DomainEvent(
        event_type=EventType.AUDIT_EXPORT_REQUESTED,
        actor=user.user_id,
        subject_type="audit_export",
        subject_id=manifest.audit_export_id,
        organization_id=user.organization_id,
        payload={"event_count": manifest.event_count, "filters": manifest.filters},
    ))
    return {"manifest": manifest.model_dump(), "events": [event.model_dump() for event in events]}


@app.get("/api/enterprise/audit-exports")
async def list_audit_exports(user: AppUser = Depends(_current_user)):
    _require_role(user, Role.ADMIN)
    manifests = await world.list_audit_export_manifests(user.organization_id)
    return [manifest.model_dump() for manifest in manifests]


@app.get("/api/enterprise/operational-summary")
async def enterprise_operational_summary(user: AppUser = Depends(_current_user)):
    requisitions, candidates, applications, interviews, offers, approvals, executions = await asyncio.gather(
        world.list_requisitions(user.organization_id, include_archived=True),
        world.list_candidates(user.organization_id),
        world.list_applications(user.organization_id, include_archived=True),
        world.list_interviews(user.organization_id),
        world.list_offers(user.organization_id),
        governance.list_approvals(user.organization_id),
        runtime.list_executions(user.organization_id),
    )
    return {
        "requisitions": {"total": len(requisitions), "open": sum(item.approval_status.value == "open" for item in requisitions)},
        "candidates": {"total": len(candidates)},
        "applications": {"total": len(applications), "hired": sum(item.status.value == "hired" for item in applications)},
        "interviews": {"total": len(interviews), "scheduled": sum(item.status.value == "scheduled" for item in interviews)},
        "offers": {"total": len(offers), "accepted": sum(item.status.value == "accepted" for item in offers)},
        "governance": {"pending_approvals": sum(item.status == "pending" for item in approvals), "executions": len(executions)},
    }


@app.get("/api/enterprise/administration/readiness")
async def enterprise_administration_readiness(user: AppUser = Depends(_current_user)):
    _require_role(user, Role.ADMIN)
    return {
        "roles": [{"id": role.value, "label": role.value.replace("_", " ").title()} for role in Role],
        "sso_saml": {
            "status": "not_configured",
            "required_configuration": ["identity_provider_metadata_url", "entity_id", "x509_certificate", "allowed_email_domains"],
            "secret_handling": "Provide identity-provider secrets through deployment configuration; EAROS does not persist them in tenant records.",
        },
        "audit_exports": {"retention_days": 30, "delivery": "authenticated API response; external storage connector required for long-lived export files"},
        "retention": {"execution": "approved cases execute only through the policy-evaluated runtime", "destructive_actions": "administrator review, legal-hold validation, tenant-scoped capability controls, and runtime approval policies are required"},
    }


# ============================================================
#   REFLECTION
# ============================================================

@app.get("/api/reflection/reports")
async def list_reflections(user: AppUser = Depends(_current_user)):
    reports = await reflection.list_reports(user.organization_id)
    return [r.model_dump() for r in reports]


# ============================================================
#   APPLICATIONS — thin composites for UI dashboards
# ============================================================

@app.get("/api/apps/dashboard/summary")
async def dashboard_summary(user: AppUser = Depends(_current_user)):
    org = await world.get_organization(user.organization_id)
    jobs = await world.list_jobs(user.organization_id)
    candidates = await world.list_candidates(user.organization_id)
    offers = await world.list_offers(user.organization_id)

    open_jobs = [j for j in jobs if j.status.value == "open"]
    hired = [c for c in candidates if c.stage == PipelineStage.HIRED]
    in_pipeline = [c for c in candidates if c.stage not in
                   (PipelineStage.HIRED, PipelineStage.REJECTED, PipelineStage.WITHDRAWN)]

    stage_counts: dict[str, int] = {}
    for c in candidates:
        stage_counts[c.stage.value] = stage_counts.get(c.stage.value, 0) + 1

    country_split: dict[str, int] = {}
    for j in open_jobs:
        country_split[j.country] = country_split.get(j.country, 0) + 1

    priority_split: dict[str, int] = {}
    for j in open_jobs:
        priority_split[j.priority] = priority_split.get(j.priority, 0) + 1

    return {
        "organization": org.model_dump() if org else None,
        "kpis": {
            "open_reqs": len(open_jobs),
            "total_candidates": len(candidates),
            "in_pipeline": len(in_pipeline),
            "hired_ytd": len(hired),
            "offers_active": len([o for o in offers if o.status.value in
                                  ("extended", "pending_approval")]),
            "avg_time_to_fill_days": 32,  # deterministic demo value
        },
        "pipeline_by_stage": stage_counts,
        "reqs_by_country": country_split,
        "reqs_by_priority": priority_split,
    }


@app.get("/api/apps/recruiter/pipeline")
async def recruiter_pipeline(user: AppUser = Depends(_current_user)):
    jobs = await world.list_jobs(user.organization_id)
    result = []
    for j in jobs:
        cands = await world.list_candidates(user.organization_id, job_id=j.job_id)
        result.append({
            "job": j.model_dump(),
            "candidate_count": len(cands),
            "by_stage": {
                s.value: len([c for c in cands if c.stage == s])
                for s in PipelineStage
            },
        })
    return result


@app.get("/api/apps/candidate/{candidate_id}/status")
async def candidate_status(candidate_id: str, user: AppUser = Depends(_current_user)):
    """Tenant-scoped view for the candidate assistant."""
    c = await _scoped_candidate(candidate_id, user)
    j = await _scoped_job(c.job_id, user)
    return {
        "candidate_id": c.candidate_id,
        "full_name": c.full_name,
        "job_title": j.title if j else "-",
        "location": j.location if j else c.location,
        "stage": c.stage.value,
        "next_step": {
            PipelineStage.SOURCED: "Recruiter will reach out shortly",
            PipelineStage.SCREENING: "Awaiting recruiter screen",
            PipelineStage.PHONE_SCREEN: "Phone screen to be scheduled",
            PipelineStage.TECHNICAL: "Technical interview to be scheduled",
            PipelineStage.ONSITE: "Onsite loop being scheduled",
            PipelineStage.OFFER: "Offer will be extended soon",
            PipelineStage.HIRED: "Welcome to LevelShift!",
            PipelineStage.REJECTED: "We won't be moving forward",
            PipelineStage.WITHDRAWN: "You withdrew from this process",
        }[c.stage],
    }


# ============================================================
#   MISSION CONTROL — live snapshot
# ============================================================

@app.get("/api/mission/snapshot")
async def mission(user: AppUser = Depends(_current_user)):
    return await mission_snapshot(db, user.organization_id)


# ============================================================
#   AGENTS + INTEGRATIONS
# ============================================================

@app.get("/api/platform/agents")
async def get_agents(user: AppUser = Depends(_current_user)):
    return [a.model_dump() for a in list_agents()]


@app.get("/api/platform/integrations")
async def integrations(user: AppUser = Depends(_current_user)):
    return [i.model_dump() for i in list_integrations()]


@app.get("/api/ats/job-distribution/adapters")
async def list_job_distribution_adapters(user: AppUser = Depends(_current_user)):
    """Expose provider capability and setup state without exposing connection secrets."""
    return [adapter.model_dump() for adapter in integration_job_distribution_adapters()]


class NotificationPreferenceUpdateRequest(BaseModel):
    in_app_enabled: bool = True
    email_enabled: bool = False
    interview_reminders: bool = True
    approval_alerts: bool = True
    candidate_activity_alerts: bool = True


class CandidateNotificationDeliveryCreateRequest(BaseModel):
    notification_type: str = Field(min_length=3, max_length=120)
    channel: str = Field(default="email", min_length=3, max_length=40)
    subject: Optional[str] = Field(default=None, max_length=500)
    body: Optional[str] = Field(default=None, max_length=10000)


class RecruiterAlertCreateRequest(BaseModel):
    recipient_user_id: str = Field(min_length=3, max_length=200)
    alert_type: str = Field(min_length=3, max_length=120)
    title: str = Field(min_length=3, max_length=300)
    body: Optional[str] = Field(default=None, max_length=4000)
    entity_type: Optional[str] = Field(default=None, max_length=100)
    entity_id: Optional[str] = Field(default=None, max_length=200)


@app.get("/api/ats/notifications/preferences")
async def get_ats_notification_preferences(user: AppUser = Depends(_current_user)):
    preference = await world.get_notification_preference(user.organization_id, user.user_id)
    if preference:
        return preference.model_dump()
    return NotificationPreference(organization_id=user.organization_id, user_id=user.user_id).model_dump()


@app.put("/api/ats/notifications/preferences")
async def update_ats_notification_preferences(
    req: NotificationPreferenceUpdateRequest, user: AppUser = Depends(_current_user)
):
    existing = await world.get_notification_preference(user.organization_id, user.user_id)
    preference = existing or NotificationPreference(organization_id=user.organization_id, user_id=user.user_id)
    for field, value in req.model_dump().items():
        setattr(preference, field, value)
    preference = await world.upsert_notification_preference(preference)
    await governance.emit(DomainEvent(
        event_type=EventType.NOTIFICATION_PREFERENCE_UPDATED,
        actor=f"user:{user.user_id}",
        subject_type="notification_preference",
        subject_id=preference.notification_preference_id,
        organization_id=user.organization_id,
        payload={"in_app_enabled": preference.in_app_enabled, "email_enabled": preference.email_enabled, "provider_delivery_state": preference.provider_delivery_state},
    ))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="notification_preference",
        entity_id=user.user_id,
        event_type="notification.preferences_updated",
        actor_user_id=user.user_id,
        payload={"in_app_enabled": preference.in_app_enabled, "email_enabled": preference.email_enabled},
    ))
    return preference.model_dump()


@app.get("/api/ats/candidates/{candidate_id}/notification-deliveries")
async def list_ats_candidate_notification_deliveries(candidate_id: str, user: AppUser = Depends(_current_user)):
    _require_role(user, Role.ADMIN, Role.RECRUITER, Role.HIRING_MANAGER)
    await _scoped_candidate(candidate_id, user)
    return [delivery.model_dump() for delivery in await world.list_candidate_notification_deliveries(
        user.organization_id, candidate_id
    )]


@app.post("/api/ats/candidates/{candidate_id}/notification-deliveries")
async def record_ats_candidate_notification_delivery(
    candidate_id: str, req: CandidateNotificationDeliveryCreateRequest, user: AppUser = Depends(_current_user)
):
    """Record a candidate notification intent; no provider message is sent by this endpoint."""
    _require_role(user, Role.ADMIN, Role.RECRUITER)
    await _scoped_candidate(candidate_id, user)
    normalized_channel = req.channel.strip().lower()
    consent = None
    if normalized_channel in {"email", "sms"}:
        consent = _has_active_recruiting_consent(
            await world.list_candidate_consents(user.organization_id, candidate_id)
        )
        if not consent:
            raise HTTPException(status_code=409, detail="Active recruiting consent is required before recording candidate email or SMS notification")
    delivery = await world.record_candidate_notification_delivery(CandidateNotificationDelivery(
        organization_id=user.organization_id,
        candidate_id=candidate_id,
        notification_type=req.notification_type,
        channel=normalized_channel,
        subject=req.subject,
        body=req.body,
        consent_id=consent.consent_id if consent else None,
        created_by_user_id=user.user_id,
    ))
    await governance.emit(DomainEvent(
        event_type=EventType.CANDIDATE_NOTIFICATION_RECORDED,
        actor=f"user:{user.user_id}",
        subject_type="candidate",
        subject_id=candidate_id,
        organization_id=user.organization_id,
        payload={"delivery_id": delivery.candidate_notification_delivery_id, "notification_type": delivery.notification_type, "channel": delivery.channel, "delivery_state": delivery.delivery_state},
    ))
    await world.record_activity(ActivityRecord(
        organization_id=user.organization_id,
        entity_type="candidate",
        entity_id=candidate_id,
        event_type="candidate.notification_recorded",
        actor_user_id=user.user_id,
        payload={"delivery_id": delivery.candidate_notification_delivery_id, "notification_type": delivery.notification_type, "channel": delivery.channel, "consent_id": delivery.consent_id, "delivery_state": delivery.delivery_state},
    ))
    return delivery.model_dump()


@app.get("/api/ats/notifications/alerts")
async def list_ats_recruiter_alerts(unread_only: bool = False, user: AppUser = Depends(_current_user)):
    _require_role(user, Role.ADMIN, Role.RECRUITER, Role.HIRING_MANAGER)
    return [alert.model_dump() for alert in await world.list_recruiter_alerts(
        user.organization_id, user.user_id, unread_only=unread_only
    )]


@app.post("/api/ats/notifications/alerts")
async def create_ats_recruiter_alert(
    req: RecruiterAlertCreateRequest, user: AppUser = Depends(_current_user)
):
    _require_role(user, Role.ADMIN, Role.RECRUITER, Role.HIRING_MANAGER)
    recipient = await db.users.find_one(
        {"user_id": req.recipient_user_id, "organization_id": user.organization_id}, {"_id": 0}
    )
    if not recipient:
        raise HTTPException(status_code=404, detail="Alert recipient not found in this organization")
    alert = await world.create_recruiter_alert(RecruiterAlert(
        organization_id=user.organization_id,
        recipient_user_id=req.recipient_user_id,
        alert_type=req.alert_type,
        title=req.title,
        body=req.body,
        entity_type=req.entity_type,
        entity_id=req.entity_id,
        created_by_user_id=user.user_id,
    ))
    await governance.emit(DomainEvent(
        event_type=EventType.RECRUITER_ALERT_CREATED,
        actor=f"user:{user.user_id}",
        subject_type="recruiter_alert",
        subject_id=alert.recruiter_alert_id,
        organization_id=user.organization_id,
        payload={"recipient_user_id": alert.recipient_user_id, "alert_type": alert.alert_type, "entity_type": alert.entity_type, "entity_id": alert.entity_id},
    ))
    return alert.model_dump()


@app.post("/api/ats/notifications/alerts/{recruiter_alert_id}/read")
async def mark_ats_recruiter_alert_read(recruiter_alert_id: str, user: AppUser = Depends(_current_user)):
    _require_role(user, Role.ADMIN, Role.RECRUITER, Role.HIRING_MANAGER)
    alert = await world.mark_recruiter_alert_read(user.organization_id, user.user_id, recruiter_alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await governance.emit(DomainEvent(
        event_type=EventType.RECRUITER_ALERT_READ,
        actor=f"user:{user.user_id}",
        subject_type="recruiter_alert",
        subject_id=alert.recruiter_alert_id,
        organization_id=user.organization_id,
        payload={"alert_type": alert.alert_type},
    ))
    return alert.model_dump()


# ============================================================
#   POLICY — CRUD + simulation
# ============================================================

class PolicyUpsertRequest(BaseModel):
    policy_id: Optional[str] = None
    name: str
    description: str
    scope: str = "*"
    applies_to_roles: list[str] = Field(default_factory=lambda: ["*"])
    max_sensitivity: Optional[str] = None
    min_confidence: Optional[float] = None
    requires_human_approval: bool = False
    enabled: bool = True


@app.post("/api/platform/policies")
async def upsert_policy(req: PolicyUpsertRequest, user: AppUser = Depends(_current_user)):
    _require_role(user, Role.ADMIN)
    p = Policy(organization_id=user.organization_id, **{k: v for k, v in req.model_dump().items() if v is not None})
    return (await policy_engine.upsert_policy(p)).model_dump()


@app.delete("/api/platform/policies/{policy_id}")
async def delete_policy(policy_id: str, user: AppUser = Depends(_current_user)):
    _require_role(user, Role.ADMIN)
    result = await db.policies.delete_one({"policy_id": policy_id, "organization_id": user.organization_id})
    if result.deleted_count != 1:
        raise HTTPException(404, "policy not found")
    return {"ok": True}


class PolicySimulateRequest(BaseModel):
    capability_id: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    sensitivity: str = "internal"


@app.post("/api/platform/policies/simulate")
async def simulate_policy(req: PolicySimulateRequest, user: AppUser = Depends(_current_user)):
    ctx = PolicyContext(
        organization_id=user.organization_id,
        user_id=user.user_id,
        user_role=user.role,
        capability_id=req.capability_id,
        sensitivity=Sensitivity(req.sensitivity),
        confidence=req.confidence,
    )
    result = await policy_engine.evaluate(ctx)
    return result.model_dump()


# ============================================================
#   INTAKE — conversational hiring
# ============================================================

class IntakeRequest(BaseModel):
    brief: str = Field(min_length=20, max_length=20_000)


def _match_job_to_intake(intake: dict[str, Any], jobs: list[Any]) -> Optional[str]:
    """Fuzzy-match an intake result to the closest seeded job by
    title tokens + location + skill overlap. Best-effort, deterministic.
    """
    if not jobs:
        return None
    role = (intake.get("role_title") or "").lower()
    location = (intake.get("location") or "").lower()
    must_haves = {s.lower() for s in (intake.get("must_have_skills") or [])}
    role_tokens = {t for t in role.replace("/", " ").split() if len(t) > 2}

    def score(job: Any) -> float:
        title = (getattr(job, "title", "") or "").lower()
        loc = (getattr(job, "location", "") or "").lower()
        skills = {s.lower() for s in (getattr(job, "required_skills", []) or [])}
        s = 0.0
        s += sum(1.5 for t in role_tokens if t in title)
        if location and location in loc:
            s += 3.0
        s += 2.0 * len(must_haves & skills)
        return s

    ranked = sorted(jobs, key=score, reverse=True)
    if score(ranked[0]) <= 0.0:
        return None
    return ranked[0].job_id


def _build_sourcing_plan(intake: dict[str, Any]) -> dict[str, Any]:
    """Turn recommended channels into an executable, staged sourcing plan."""
    channels = intake.get("recommended_sourcing_channels") or []
    must = intake.get("must_have_skills") or []
    location = intake.get("location") or ""
    headcount = intake.get("headcount") or 1

    # Wave 1: P0 channels, Wave 2: P1, Wave 3: P2
    waves = []
    for tier, label in [("P0", "Wave 1 · Priority sweep"),
                        ("P1", "Wave 2 · Expansion sweep"),
                        ("P2", "Wave 3 · Long-tail")]:
        tier_chans = [c for c in channels if c.get("priority") == tier]
        if tier_chans:
            waves.append({
                "wave": label,
                "channels": tier_chans,
                "target_candidates": (5 * headcount) if tier == "P0"
                                     else (3 * headcount) if tier == "P1"
                                     else (2 * headcount),
            })

    # Fallback if the LLM returned no channels
    if not waves:
        waves = [{
            "wave": "Wave 1 · Priority sweep",
            "channels": [
                {"channel": "LinkedIn Recruiter", "priority": "P0",
                 "why": f"Deepest pool for {location or 'this market'}."},
                {"channel": "GitHub", "priority": "P0",
                 "why": "Signal on actual code and OSS contribution."},
                {"channel": "Internal ATS", "priority": "P1",
                 "why": "Silver-medalist candidates from prior reqs."},
            ],
            "target_candidates": 5 * headcount,
        }]

    return {
        "waves": waves,
        "search_string": " AND ".join(
            [f'"{s}"' for s in must[:4]] + ([f'"{location}"'] if location else [])
        ),
        "estimated_sweep_minutes": 6 + 2 * len(waves),
        "estimated_reach_candidates": sum(w["target_candidates"] for w in waves),
    }


@app.post("/api/intake/analyze")
async def intake_analyze(req: IntakeRequest, user: AppUser = Depends(_current_user)):
    intake = await run_intake(req.brief)
    rec = intake_to_recommendation(req.brief, intake)
    jobs = await world.list_jobs(user.organization_id)
    matched_job_id = _match_job_to_intake(intake, jobs)
    sourcing_plan = _build_sourcing_plan(intake)
    return {
        "intake": intake,
        "recommendation": rec.model_dump(),
        "matched_job_id": matched_job_id,
        "sourcing_plan": sourcing_plan,
    }


# ============================================================
#   SOURCING — parallel multi-source sweep (simulated)
# ============================================================

@app.get("/api/sourcing/sweep/{job_id}")
async def sourcing(job_id: str, user: AppUser = Depends(_current_user)):
    await _scoped_job(job_id, user)
    return await sourcing_sweep(world, job_id)


# ============================================================
#   RESUME INTELLIGENCE
# ============================================================

class ResumeRequest(BaseModel):
    resume_text: str = Field(min_length=20, max_length=200_000)
    job_id: Optional[str] = None
    candidate_alias: Optional[str] = None


@app.post("/api/resume/analyze")
async def resume_analyze(req: ResumeRequest, user: AppUser = Depends(_current_user)):
    parsed = resume_parse(req.resume_text)
    fit = None
    client = None
    redacted = resume_redact(parsed)
    if req.job_id:
        await _scoped_job(req.job_id, user)
        fit = await resume_fit(world, req.job_id, parsed)
        if fit and "error" not in fit:
            client = resume_client_summary(parsed, fit, req.candidate_alias or "Candidate-A")
    return {"parsed": parsed, "redacted": redacted, "fit": fit,
            "client_summary": client}


# ============================================================
#   OUTREACH
# ============================================================

@app.get("/api/outreach/pack/{candidate_id}")
async def outreach_pack(candidate_id: str, user: AppUser = Depends(_current_user)):
    await _scoped_candidate(candidate_id, user)
    return await draft_outreach_pack(world, user.organization_id, candidate_id)


# ============================================================
#   SCREENING RUBRIC
# ============================================================

class RubricRequest(BaseModel):
    candidate_id: str
    notes: str = ""


@app.post("/api/screening/rubric")
async def screening_rubric(req: RubricRequest, user: AppUser = Depends(_current_user)):
    await _scoped_candidate(req.candidate_id, user)
    return await screen_rubric(world, req.candidate_id, req.notes)


# ============================================================
#   VOICE INTERVIEW
# ============================================================

@app.get("/api/voice/plan/{candidate_id}")
async def voice_plan(candidate_id: str, user: AppUser = Depends(_current_user)):
    await _scoped_candidate(candidate_id, user)
    return await voice_start(world, candidate_id)


@app.get("/api/voice/turn/{candidate_id}/{question_index}")
async def voice_turn_ep(candidate_id: str, question_index: int,
                        user: AppUser = Depends(_current_user)):
    await _scoped_candidate(candidate_id, user)
    return await voice_turn(world, candidate_id, question_index)


class VoiceSummarizeRequest(BaseModel):
    candidate_id: str
    turns: list[dict[str, Any]] = Field(default_factory=list)


@app.post("/api/voice/summarize")
async def voice_summarize_ep(req: VoiceSummarizeRequest,
                              user: AppUser = Depends(_current_user)):
    await _scoped_candidate(req.candidate_id, user)
    return await voice_summarize(world, req.candidate_id, req.turns)


# ============================================================
#   EXECUTIVE SIMULATION
# ============================================================

class SimRequest(BaseModel):
    attrition_pct: float = 0.12
    hiring_freeze: bool = False
    budget_delta_pct: float = 0.0
    bangalore_expansion: bool = False
    ai_engineering_doubles: bool = False
    horizon_months: int = 12


@app.post("/api/simulate/what-if")
async def what_if(req: SimRequest, user: AppUser = Depends(_current_user)):
    return await sim_simulate(world, user.organization_id, **req.model_dump())


# ============================================================
#   DEMO SCENARIOS
# ============================================================

@app.get("/api/scenarios")
async def scenarios(user: AppUser = Depends(_current_user)):
    return list_scenarios()


@app.post("/api/scenarios/{scenario_id}/run")
async def run_scenario_ep(scenario_id: str, user: AppUser = Depends(_current_user)):
    """Start a paced scenario execution. Returns immediately with an
    execution_id that the client polls via /executions/{id}/state."""
    scenario = next(
        (s for s in list_scenarios() if s["scenario_id"] == scenario_id), None,
    )
    if not scenario:
        raise HTTPException(404, "scenario not found")
    state = scenario_tracker.create(
        scenario_id=scenario_id,
        scenario_title=scenario["title"],
        step_defs=build_scenario_steps(),
    )
    task = asyncio.create_task(run_scenario_paced(
        state.execution_id, scenario_id,
        user.organization_id, user.user_id,
        world, runtime, policy_engine, governance, reflection,
    ))
    scenario_tracker.attach_task(state.execution_id, task)
    return state.to_dict()


@app.get("/api/scenarios/executions/{execution_id}/state")
async def scenario_state(execution_id: str, user: AppUser = Depends(_current_user)):
    state = scenario_tracker.get(execution_id)
    if not state:
        raise HTTPException(404, "execution not found")
    return state.to_dict()


@app.post("/api/scenarios/executions/{execution_id}/approve")
async def scenario_approve(execution_id: str, user: AppUser = Depends(_current_user)):
    ok = scenario_tracker.approve(execution_id)
    if not ok:
        raise HTTPException(400, "no pending approval on this execution")
    return {"ok": True, "decision": "approved"}


@app.post("/api/scenarios/executions/{execution_id}/reject")
async def scenario_reject(execution_id: str, user: AppUser = Depends(_current_user)):
    ok = scenario_tracker.reject(execution_id)
    if not ok:
        raise HTTPException(400, "no pending approval on this execution")
    return {"ok": True, "decision": "rejected"}


# Legacy synchronous runner kept for tests / programmatic access.
@app.post("/api/scenarios/{scenario_id}/run-sync")
async def run_scenario_sync_ep(scenario_id: str, user: AppUser = Depends(_current_user)):
    return await run_scenario(
        scenario_id, user.organization_id, user.user_id,
        world, runtime, policy_engine, governance, reflection,
    )


# ============================================================
#   DEEP-DIVE / REPLAY
# ============================================================

@app.get("/api/deep-dive/executions")
async def deep_dive_list(user: AppUser = Depends(_current_user)):
    return await list_replayable_executions(db, user.organization_id)


@app.get("/api/deep-dive/replay/{correlation_id}")
async def deep_dive_replay(correlation_id: str, user: AppUser = Depends(_current_user)):
    result = await replay_execution(db, correlation_id)
    if not result["messages"]:
        raise HTTPException(404, "no events for this correlation id")
    return result


@app.on_event("startup")
async def _on_startup():
    logger.info("EAROS starting up — seeding world state (idempotent)")
    try:
        result = await seed_all(db)
        logger.info(f"Seed complete: {result}")
    except Exception as exc:
        logger.exception(f"Seed failed: {exc}")


@app.on_event("shutdown")
async def _on_shutdown():
    mongo_client.close()
