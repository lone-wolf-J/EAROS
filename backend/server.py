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

import logging
import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from applications.auth import AppUser, build_router as build_auth_router, get_current_user
from foundation import (
    ExecutionStatus,
    PipelineStage,
    Recommendation,
    Sensitivity,
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
from platform_core.capabilities import build_default_registry
from platform_core.governance import Governance
from platform_core.memory import Memory
from platform_core.planner import Planner
from platform_core.policy import PolicyEngine
from platform_core.reflection import Reflection
from platform_core.runtime import ExecutionRecord, PlanStep, Runtime
from platform_core.world import WorldState
from seed import seed_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("earos")

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

app = FastAPI(title="EAROS", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _current_user(request: Request) -> AppUser:
    return await get_current_user(request, db)


# ---------- Auth router ----------
app.include_router(build_auth_router(db))


# ============================================================
#   HEALTH + BOOTSTRAP
# ============================================================

@app.get("/api/health")
async def health():
    return {"ok": True, "service": "EAROS", "time": utcnow_iso()}


@app.post("/api/bootstrap")
async def bootstrap():
    """Seed World State + policies + demo users. Idempotent."""
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
    j = await world.get_job(job_id)
    if not j:
        raise HTTPException(404, "job not found")
    return j.model_dump()


@app.get("/api/world/jobs/{job_id}/candidates")
async def list_job_candidates(
    job_id: str,
    stage: Optional[str] = None,
    user: AppUser = Depends(_current_user),
):
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
    c = await world.get_candidate(candidate_id)
    if not c:
        raise HTTPException(404, "candidate not found")
    return c.model_dump()


@app.get("/api/world/offers")
async def list_offers(user: AppUser = Depends(_current_user)):
    return [o.model_dump() for o in await world.list_offers(user.organization_id)]


# ============================================================
#   INTELLIGENCE — recommendations (never execute)
# ============================================================

@app.get("/api/intelligence/hiring/{job_id}")
async def hiring_recs(job_id: str, top_n: int = 5, user: AppUser = Depends(_current_user)):
    recs = await hiring_recommendations_for_job(world, user.organization_id, job_id, top_n=top_n)
    return {"job_id": job_id, "recommendations": [r.model_dump() for r in recs]}


@app.get("/api/intelligence/offer/{candidate_id}")
async def offer_rec(candidate_id: str, user: AppUser = Depends(_current_user)):
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
    goal: str
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
    return [p.model_dump() for p in await policy_engine.list_policies()]


# ============================================================
#   RUNTIME — the ONLY layer that executes business actions
# ============================================================

class ExecuteRequest(BaseModel):
    goal: str
    steps: list[dict[str, Any]]
    decision_id: Optional[str] = None


@app.post("/api/runtime/execute")
async def execute_plan(req: ExecuteRequest, user: AppUser = Depends(_current_user)):
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
    if req.decision not in ("granted", "denied"):
        raise HTTPException(400, "decision must be 'granted' or 'denied'")
    a = await governance.decide_approval(approval_id, req.decision, user.user_id, req.note)
    if not a:
        raise HTTPException(404, "approval not found")
    return a.model_dump()


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
    """Public-safe view for the candidate assistant."""
    c = await world.get_candidate(candidate_id)
    if not c:
        raise HTTPException(404, "candidate not found")
    j = await world.get_job(c.job_id)
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
