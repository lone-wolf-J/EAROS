"""Capability Registry + built-in capabilities.

Every capability registers:
  metadata, permissions, input schema, output schema, health, dependencies,
  supported actions, version.

Capabilities are deterministic. They own business actions.
The LLM never invokes a capability directly — always via the Runtime.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

from pydantic import BaseModel, ConfigDict, Field

from foundation import Sensitivity, new_capability_id, utcnow_iso
from platform_core.world import PipelineStage, WorldState


class CapabilitySpec(BaseModel):
    model_config = ConfigDict(extra="ignore")
    capability_id: str
    name: str
    description: str
    category: str  # sourcing | screening | interview | offer | ops
    version: str = "1.0.0"
    inputs: dict[str, str] = Field(default_factory=dict)  # name -> type-hint string
    outputs: dict[str, str] = Field(default_factory=dict)
    permissions: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    deterministic: bool = True
    health: str = "healthy"
    registered_at: str = Field(default_factory=utcnow_iso)


class CapabilityResult(BaseModel):
    ok: bool
    output: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    facts: list[str] = Field(default_factory=list)  # human-readable trace


CapabilityHandler = Callable[[dict[str, Any], "CapabilityContext"], Awaitable[CapabilityResult]]


class CapabilityContext(BaseModel):
    organization_id: str
    user_id: str
    execution_id: str
    correlation_id: str
    world: Any  # WorldState  (not typed strictly to avoid circular hint)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class CapabilityRegistry:
    """In-memory registry keyed by capability_id."""

    def __init__(self):
        self._specs: dict[str, CapabilitySpec] = {}
        self._handlers: dict[str, CapabilityHandler] = {}

    def register(self, spec: CapabilitySpec, handler: CapabilityHandler) -> None:
        self._specs[spec.capability_id] = spec
        self._handlers[spec.capability_id] = handler

    def get_spec(self, capability_id: str) -> Optional[CapabilitySpec]:
        return self._specs.get(capability_id)

    def get_handler(self, capability_id: str) -> Optional[CapabilityHandler]:
        return self._handlers.get(capability_id)

    def list_specs(self) -> list[CapabilitySpec]:
        return list(self._specs.values())


# ============================================================
#   BUILT-IN CAPABILITIES
# ============================================================

async def cap_source_candidates(
    inputs: dict[str, Any], ctx: CapabilityContext
) -> CapabilityResult:
    """Deterministic sourcing: filters world state for candidates matching a job."""
    world: WorldState = ctx.world
    job_id = inputs["job_id"]
    limit = int(inputs.get("limit", 20))
    job = await world.get_job(job_id)
    if not job:
        return CapabilityResult(ok=False, error=f"job {job_id} not found")
    candidates = await world.list_candidates(ctx.organization_id, job_id=job_id)
    matches = [c for c in candidates if c.stage == PipelineStage.SOURCED][:limit]
    return CapabilityResult(
        ok=True,
        output={"candidate_ids": [c.candidate_id for c in matches], "count": len(matches)},
        facts=[f"sourced {len(matches)} candidates for {job.title}"],
    )


async def cap_screen_candidate(
    inputs: dict[str, Any], ctx: CapabilityContext
) -> CapabilityResult:
    """Deterministic screen based on skill overlap and experience heuristics."""
    world: WorldState = ctx.world
    candidate_id = inputs["candidate_id"]
    cand = await world.get_candidate(candidate_id)
    if not cand:
        return CapabilityResult(ok=False, error="candidate not found")
    job = await world.get_job(cand.job_id)
    if not job:
        return CapabilityResult(ok=False, error="job not found")

    req = set(s.lower() for s in job.required_skills)
    have = set(s.lower() for s in cand.skills)
    overlap = req & have
    coverage = len(overlap) / max(1, len(req))
    exp_fit = min(1.0, cand.years_experience / 8.0)
    fit = round(0.7 * coverage + 0.3 * exp_fit, 3)

    await world.db.candidates.update_one(
        {"candidate_id": candidate_id},
        {"$set": {"fit_score": fit, "stage": PipelineStage.SCREENING.value}},
    )
    return CapabilityResult(
        ok=True,
        output={"candidate_id": candidate_id, "fit_score": fit, "coverage": round(coverage, 3)},
        facts=[
            f"skill coverage {coverage:.0%} ({len(overlap)}/{len(req)})",
            f"years-experience fit {exp_fit:.2f}",
            f"final fit score {fit:.3f}",
        ],
    )


async def cap_advance_stage(
    inputs: dict[str, Any], ctx: CapabilityContext
) -> CapabilityResult:
    world: WorldState = ctx.world
    candidate_id = inputs["candidate_id"]
    target_stage = inputs["stage"]
    try:
        stage = PipelineStage(target_stage)
    except ValueError:
        return CapabilityResult(ok=False, error=f"invalid stage {target_stage}")
    cand = await world.get_candidate(candidate_id)
    if not cand:
        return CapabilityResult(ok=False, error="candidate not found")
    await world.set_candidate_stage(candidate_id, stage)
    return CapabilityResult(
        ok=True,
        output={"candidate_id": candidate_id, "from": cand.stage.value, "to": stage.value},
        facts=[f"stage {cand.stage.value} -> {stage.value}"],
    )


async def cap_draft_outreach(
    inputs: dict[str, Any], ctx: CapabilityContext
) -> CapabilityResult:
    """Deterministic template-based outreach draft (LLM enrichment lives in Intelligence layer)."""
    world: WorldState = ctx.world
    cand = await world.get_candidate(inputs["candidate_id"])
    if not cand:
        return CapabilityResult(ok=False, error="candidate not found")
    job = await world.get_job(cand.job_id)
    if not job:
        return CapabilityResult(ok=False, error="job not found")
    subject = f"{job.title} @ LevelShift — a role we think fits your profile"
    body = (
        f"Hi {cand.full_name.split()[0]},\n\n"
        f"I'm reaching out from LevelShift about a {job.title} role in {job.location}. "
        f"Your background at {cand.current_company} and skills in "
        f"{', '.join(cand.skills[:3])} align closely with what the team is looking for.\n\n"
        "Would you be open to a 20-minute intro chat this week?\n\nBest,\nLevelShift Talent"
    )
    return CapabilityResult(
        ok=True,
        output={"subject": subject, "body": body, "channel": "email"},
        facts=["outreach draft generated from deterministic template"],
    )


async def cap_generate_offer(
    inputs: dict[str, Any], ctx: CapabilityContext
) -> CapabilityResult:
    from platform_core.world import Offer, OfferStatus
    world: WorldState = ctx.world
    cand = await world.get_candidate(inputs["candidate_id"])
    if not cand:
        return CapabilityResult(ok=False, error="candidate not found")
    job = await world.get_job(cand.job_id)
    if not job:
        return CapabilityResult(ok=False, error="job not found")

    base = int(inputs.get("base_salary", (job.salary_min + job.salary_max) // 2))
    bonus = int(base * 0.15)
    equity = int(inputs.get("equity_units", 2000))
    signing = int(inputs.get("signing_bonus", int(base * 0.05)))

    mid = (job.salary_min + job.salary_max) / 2
    market_percentile = min(1.0, max(0.0, (base - job.salary_min) / max(1, job.salary_max - job.salary_min)))
    parity_delta = round((base - mid) / max(1, mid), 3)

    offer = Offer(
        organization_id=ctx.organization_id,
        candidate_id=cand.candidate_id,
        job_id=job.job_id,
        base_salary=base,
        bonus=bonus,
        equity_units=equity,
        signing_bonus=signing,
        currency=job.currency,
        status=OfferStatus.DRAFT,
        market_percentile=round(market_percentile, 3),
        internal_parity_delta=parity_delta,
        acceptance_probability=round(0.5 + 0.35 * market_percentile, 3),
        reasoning_decision_id=inputs.get("reasoning_decision_id"),
    )
    await world.upsert_offer(offer)
    return CapabilityResult(
        ok=True,
        output=offer.model_dump(),
        facts=[
            f"base {job.currency} {base:,}",
            f"market percentile {market_percentile:.0%}",
            f"internal parity delta {parity_delta:+.2%}",
        ],
    )


async def cap_schedule_interview(
    inputs: dict[str, Any], ctx: CapabilityContext
) -> CapabilityResult:
    world: WorldState = ctx.world
    cand = await world.get_candidate(inputs["candidate_id"])
    if not cand:
        return CapabilityResult(ok=False, error="candidate not found")
    stage_str = inputs.get("stage", "phone_screen")
    await world.set_candidate_stage(cand.candidate_id, PipelineStage(stage_str))
    interviewer = inputs.get("interviewer", "Priya Menon (Engineering)")
    slot = inputs.get("slot", "Tomorrow 10:30 IST")
    return CapabilityResult(
        ok=True,
        output={
            "candidate_id": cand.candidate_id,
            "interviewer": interviewer,
            "slot": slot,
            "stage": stage_str,
        },
        facts=[f"interview scheduled with {interviewer} at {slot}"],
    )


BUILTIN_CAPABILITIES: list[tuple[CapabilitySpec, CapabilityHandler]] = [
    (
        CapabilitySpec(
            capability_id="cap.source_candidates",
            name="Source Candidates",
            description="Deterministic sourcing over world-state candidate pool.",
            category="sourcing",
            inputs={"job_id": "str", "limit": "int?"},
            outputs={"candidate_ids": "list[str]", "count": "int"},
            permissions=["world.candidates.read"],
        ),
        cap_source_candidates,
    ),
    (
        CapabilitySpec(
            capability_id="cap.screen_candidate",
            name="Screen Candidate",
            description="Rule-based fit scoring using skill overlap + experience.",
            category="screening",
            inputs={"candidate_id": "str"},
            outputs={"fit_score": "float", "coverage": "float"},
            permissions=["world.candidates.read", "world.candidates.write"],
        ),
        cap_screen_candidate,
    ),
    (
        CapabilitySpec(
            capability_id="cap.advance_stage",
            name="Advance Pipeline Stage",
            description="Transition a candidate to a specified pipeline stage.",
            category="ops",
            inputs={"candidate_id": "str", "stage": "PipelineStage"},
            outputs={"from": "str", "to": "str"},
            permissions=["world.candidates.write"],
        ),
        cap_advance_stage,
    ),
    (
        CapabilitySpec(
            capability_id="cap.draft_outreach",
            name="Draft Outreach",
            description="Deterministic outreach draft.",
            category="sourcing",
            inputs={"candidate_id": "str"},
            outputs={"subject": "str", "body": "str"},
            permissions=["world.candidates.read"],
        ),
        cap_draft_outreach,
    ),
    (
        CapabilitySpec(
            capability_id="cap.generate_offer",
            name="Generate Offer",
            description="Compose an offer package for a candidate.",
            category="offer",
            sensitivity=Sensitivity.CONFIDENTIAL,
            inputs={"candidate_id": "str", "base_salary": "int?"},
            outputs={"offer_id": "str"},
            permissions=["world.offers.write"],
        ),
        cap_generate_offer,
    ),
    (
        CapabilitySpec(
            capability_id="cap.schedule_interview",
            name="Schedule Interview",
            description="Schedule an interview and advance stage.",
            category="interview",
            inputs={"candidate_id": "str", "stage": "str?", "interviewer": "str?", "slot": "str?"},
            outputs={"interviewer": "str", "slot": "str"},
            permissions=["world.candidates.write"],
        ),
        cap_schedule_interview,
    ),
]


def build_default_registry() -> CapabilityRegistry:
    reg = CapabilityRegistry()
    for spec, handler in BUILTIN_CAPABILITIES:
        reg.register(spec, handler)
    return reg
