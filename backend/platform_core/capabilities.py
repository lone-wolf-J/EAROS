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
    """Deterministic sourcing: limits a job search to active, consented prospects."""
    world: WorldState = ctx.world
    job_id = inputs["job_id"]
    limit = int(inputs.get("limit", 20))
    job = await world.get_job_for_organization(ctx.organization_id, job_id)
    if not job:
        return CapabilityResult(ok=False, error=f"job {job_id} not found")
    candidates = await world.list_candidates(ctx.organization_id, job_id=job_id)
    matches = [
        candidate
        for candidate in candidates
        if candidate.stage == PipelineStage.SOURCED
        and candidate.archived_at is None
        and candidate.erased_at is None
        and await _has_active_recruiting_consent(world, ctx.organization_id, candidate.candidate_id)
    ][:limit]
    return CapabilityResult(
        ok=True,
        output={"candidate_ids": [c.candidate_id for c in matches], "count": len(matches)},
        facts=[
            f"sourced {len(matches)} active prospects with recorded recruiting consent for {job.title}",
            "sourcing is read-only and does not contact candidates or alter any recruiting record",
        ],
    )


async def cap_screen_candidate(
    inputs: dict[str, Any], ctx: CapabilityContext
) -> CapabilityResult:
    """Deterministic screen based on skill overlap and experience heuristics."""
    world: WorldState = ctx.world
    candidate_id = inputs["candidate_id"]
    cand = await world.get_candidate_for_organization(ctx.organization_id, candidate_id)
    if not cand:
        return CapabilityResult(ok=False, error="candidate not found")
    job = await world.get_job_for_organization(ctx.organization_id, cand.job_id)
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
    cand = await world.get_candidate_for_organization(ctx.organization_id, candidate_id)
    if not cand:
        return CapabilityResult(ok=False, error="candidate not found")
    await world.set_candidate_stage_for_organization(ctx.organization_id, candidate_id, stage)
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
    cand = await world.get_candidate_for_organization(ctx.organization_id, inputs["candidate_id"])
    if not cand:
        return CapabilityResult(ok=False, error="candidate not found")
    if not await _has_active_recruiting_consent(world, ctx.organization_id, cand.candidate_id):
        return CapabilityResult(ok=False, error="active recruiting consent is required before an outreach draft can be prepared")
    job = await world.get_job_for_organization(ctx.organization_id, cand.job_id)
    if not job:
        return CapabilityResult(ok=False, error="job not found")
    first_name = cand.full_name.split()[0] if cand.full_name.strip() else "there"
    subject = f"{job.title} at EAROS customer team — a role aligned with your profile"
    body = (
        f"Hi {first_name},\n\n"
        f"I'm reaching out about a {job.title} role in {job.location}. "
        f"Your background at {cand.current_company} and skills in "
        f"{', '.join(cand.skills[:3])} align closely with what the team is looking for.\n\n"
        "Would you be open to a 20-minute introductory conversation this week?\n\nBest,\nTalent team"
    )
    return CapabilityResult(
        ok=True,
        output={"candidate_id": cand.candidate_id, "subject": subject, "body": body, "channel": "email", "delivery_state": "draft_only"},
        facts=[
            "outreach draft generated from a deterministic template after consent verification",
            "the capability creates no communication record and never sends a message",
        ],
    )


async def cap_generate_offer(
    inputs: dict[str, Any], ctx: CapabilityContext
) -> CapabilityResult:
    from platform_core.world import Offer, OfferStatus
    world: WorldState = ctx.world
    cand = await world.get_candidate_for_organization(ctx.organization_id, inputs["candidate_id"])
    if not cand:
        return CapabilityResult(ok=False, error="candidate not found")
    job = await world.get_job_for_organization(ctx.organization_id, cand.job_id)
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
    cand = await world.get_candidate_for_organization(ctx.organization_id, inputs["candidate_id"])
    if not cand:
        return CapabilityResult(ok=False, error="candidate not found")
    stage_str = inputs.get("stage", "phone_screen")
    await world.set_candidate_stage_for_organization(ctx.organization_id, cand.candidate_id, PipelineStage(stage_str))
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


async def _requisition_skills(
    world: WorldState, organization_id: str, requisition_id: str
) -> tuple[Any, list[str]]:
    requisition = await world.get_requisition(organization_id, requisition_id)
    if not requisition:
        return None, []
    planned_skills = requisition.hiring_plan.get("required_skills", [])
    if planned_skills:
        return requisition, [str(skill) for skill in planned_skills]
    if requisition.job_id:
        job = await world.get_job_for_organization(organization_id, requisition.job_id)
        if job:
            return requisition, job.required_skills
    return requisition, []


async def _has_active_recruiting_consent(
    world: WorldState, organization_id: str, candidate_id: str
) -> bool:
    """Require recorded, unexpired recruiting consent for recommendation-stage outreach or sourcing."""
    consents = await world.list_candidate_consents(organization_id, candidate_id)
    now = utcnow_iso()
    for consent in consents:
        status = getattr(consent.status, "value", consent.status)
        if (
            consent.purpose == "recruiting"
            and status == "granted"
            and (not consent.expires_at or consent.expires_at >= now)
        ):
            return True
    return False


async def cap_source_requisition_prospects(
    inputs: dict[str, Any], ctx: CapabilityContext
) -> CapabilityResult:
    """Return a consent-aware, read-only prospect shortlist for a requisition without any outreach."""
    world: WorldState = ctx.world
    requisition_id = inputs["requisition_id"]
    requisition, required_skills = await _requisition_skills(world, ctx.organization_id, requisition_id)
    if not requisition:
        return CapabilityResult(ok=False, error="requisition not found")
    if not required_skills:
        return CapabilityResult(ok=False, error="requisition has no required skills in its hiring plan")

    required = {skill.strip().lower() for skill in required_skills if skill.strip()}
    limit = min(max(int(inputs.get("limit", 20)), 1), 100)
    prospects: list[dict[str, Any]] = []
    for candidate in await world.list_candidates(ctx.organization_id):
        if candidate.archived_at or candidate.erased_at:
            continue
        if not await _has_active_recruiting_consent(world, ctx.organization_id, candidate.candidate_id):
            continue
        candidate_skills = {skill.strip().lower() for skill in candidate.skills if skill.strip()}
        matched_skills = sorted(required & candidate_skills)
        if not matched_skills:
            continue
        coverage = len(matched_skills) / max(1, len(required))
        score = round(0.8 * coverage + 0.2 * min(candidate.years_experience / 8.0, 1.0), 3)
        prospects.append({
            "candidate_id": candidate.candidate_id,
            "score": score,
            "matched_skills": matched_skills,
            "skill_gaps": sorted(required - candidate_skills),
        })
    prospects.sort(key=lambda item: item["score"], reverse=True)
    shortlist = prospects[:limit]
    return CapabilityResult(
        ok=True,
        output={"requisition_id": requisition_id, "prospects": shortlist, "count": len(shortlist)},
        facts=[
            f"identified {len(shortlist)} in-tenant prospects with active recruiting consent",
            "shortlisting is read-only; it does not contact, tag, or advance any candidate automatically",
        ],
    )


async def cap_analyze_resume(
    inputs: dict[str, Any], ctx: CapabilityContext
) -> CapabilityResult:
    """Summarize existing parsed resume evidence without re-parsing a file or changing the candidate record."""
    world: WorldState = ctx.world
    candidate_id = inputs["candidate_id"]
    candidate = await world.get_candidate_for_organization(ctx.organization_id, candidate_id)
    if not candidate:
        return CapabilityResult(ok=False, error="candidate not found")
    resumes = await world.list_resumes(ctx.organization_id, candidate_id)
    requested_resume_id = inputs.get("resume_id")
    resume = next((item for item in resumes if item.resume_id == requested_resume_id), None) if requested_resume_id else next((item for item in resumes if item.is_primary), resumes[0] if resumes else None)
    if not resume:
        return CapabilityResult(ok=False, error="candidate has no resume record")
    if resume.parse_status != "parsed" or not resume.parsed_profile:
        return CapabilityResult(ok=False, error="resume must be parsed before a structured analysis can be prepared")

    profile = resume.parsed_profile
    raw_skills = profile.get("skills", candidate.skills)
    extracted_skills = sorted({str(skill).strip() for skill in raw_skills if str(skill).strip()})
    experience = profile.get("experience", [])
    education = profile.get("education", [])
    strengths = [
        f"Structured profile contains {len(extracted_skills)} extracted skills.",
        f"Candidate record reports {candidate.years_experience:g} years of experience.",
    ]
    limitations = []
    if not experience:
        limitations.append("The parsed profile has no structured experience timeline; a recruiter should verify chronology against the original document.")
    if not education:
        limitations.append("The parsed profile has no structured education section; a recruiter should verify education claims if relevant to the role.")
    if not extracted_skills:
        limitations.append("No usable skills were extracted; resume parsing should be reviewed or retried before scoring.")
    return CapabilityResult(
        ok=True,
        output={
            "candidate_id": candidate.candidate_id,
            "resume_id": resume.resume_id,
            "parse_status": resume.parse_status,
            "extracted_skills": extracted_skills,
            "experience_entry_count": len(experience) if isinstance(experience, list) else 0,
            "education_entry_count": len(education) if isinstance(education, list) else 0,
            "strengths": strengths,
            "limitations": limitations,
            "requires_human_review": True,
        },
        facts=[
            "analysis uses the existing parsed resume profile and canonical candidate record only",
            "analysis is read-only and is distinct from parsing, fit scoring, candidate stage changes, and hiring decisions",
        ],
    )


async def cap_match_requisition(
    inputs: dict[str, Any], ctx: CapabilityContext
) -> CapabilityResult:
    """Rank in-tenant prospects against requisition facts without altering state."""
    world: WorldState = ctx.world
    requisition_id = inputs["requisition_id"]
    requisition, required_skills = await _requisition_skills(world, ctx.organization_id, requisition_id)
    if not requisition:
        return CapabilityResult(ok=False, error="requisition not found")
    if not required_skills:
        return CapabilityResult(ok=False, error="requisition has no required skills in its hiring plan")

    limit = min(max(int(inputs.get("limit", 20)), 1), 100)
    required = {skill.strip().lower() for skill in required_skills if skill.strip()}
    matches: list[dict[str, Any]] = []
    for candidate in await world.list_candidates(ctx.organization_id):
        candidate_skills = {skill.strip().lower() for skill in candidate.skills if skill.strip()}
        overlap = sorted(required & candidate_skills)
        coverage = len(overlap) / max(1, len(required))
        experience_signal = min(candidate.years_experience / 8.0, 1.0)
        score = round(0.8 * coverage + 0.2 * experience_signal, 3)
        if overlap:
            matches.append({
                "candidate_id": candidate.candidate_id,
                "score": score,
                "matched_skills": overlap,
                "skill_gaps": sorted(required - candidate_skills),
            })
    matches.sort(key=lambda item: item["score"], reverse=True)
    ranked = matches[:limit]
    return CapabilityResult(
        ok=True,
        output={"requisition_id": requisition_id, "matches": ranked, "count": len(ranked)},
        facts=[
            f"compared {len(matches)} eligible prospects against {len(required)} required skills",
            "ranking is deterministic and does not change candidate or application state",
        ],
    )


async def cap_score_application(
    inputs: dict[str, Any], ctx: CapabilityContext
) -> CapabilityResult:
    """Persist explainable skill-fit analysis through the governed runtime only."""
    world: WorldState = ctx.world
    application = await world.get_application(ctx.organization_id, inputs["application_id"])
    if not application:
        return CapabilityResult(ok=False, error="application not found")
    if not application.requisition_id:
        return CapabilityResult(ok=False, error="application has no requisition context")
    candidate = await world.get_candidate_for_organization(ctx.organization_id, application.candidate_id)
    if not candidate:
        return CapabilityResult(ok=False, error="candidate not found")
    requisition, required_skills = await _requisition_skills(world, ctx.organization_id, application.requisition_id)
    if not requisition or not required_skills:
        return CapabilityResult(ok=False, error="requisition skill requirements are unavailable")

    required = {skill.strip().lower() for skill in required_skills if skill.strip()}
    candidate_skills = {skill.strip().lower() for skill in candidate.skills if skill.strip()}
    overlap = sorted(required & candidate_skills)
    gaps = sorted(required - candidate_skills)
    coverage = len(overlap) / max(1, len(required))
    experience_signal = min(candidate.years_experience / 8.0, 1.0)
    fit_score = round(0.75 * coverage + 0.25 * experience_signal, 3)
    summary = f"Matched {len(overlap)} of {len(required)} required skills; experience signal {experience_signal:.0%}."
    await world.db.applications.update_one(
        {"organization_id": ctx.organization_id, "application_id": application.application_id},
        {"$set": {"fit_score": fit_score, "score_summary": summary, "skill_gaps": gaps}},
    )
    return CapabilityResult(
        ok=True,
        output={"application_id": application.application_id, "fit_score": fit_score, "matched_skills": overlap, "skill_gaps": gaps},
        facts=[summary, "application fit score updated by a deterministic governed capability"],
    )


async def cap_prepare_interview(
    inputs: dict[str, Any], ctx: CapabilityContext
) -> CapabilityResult:
    """Produce an interview brief from persisted candidate, requisition, and scorecard facts."""
    world: WorldState = ctx.world
    interview = await world.get_interview(ctx.organization_id, inputs["interview_id"])
    if not interview:
        return CapabilityResult(ok=False, error="interview not found")
    application = await world.get_application(ctx.organization_id, interview.application_id)
    candidate = await world.get_candidate_for_organization(ctx.organization_id, interview.candidate_id)
    if not application or not candidate:
        return CapabilityResult(ok=False, error="interview context is incomplete")
    requisition, skills = await _requisition_skills(world, ctx.organization_id, application.requisition_id) if application.requisition_id else (None, [])
    scorecards = await world.list_scorecards(ctx.organization_id, application.requisition_id)
    focus_skills = skills[:5] or candidate.skills[:5]
    agenda = [
        {"section": "Role context", "minutes": 5, "prompt": f"Explain the role and validate interest in {requisition.title if requisition else 'the opportunity'}."},
        {"section": "Evidence interview", "minutes": 25, "prompt": f"Request structured examples related to {', '.join(focus_skills) or 'role-relevant competencies'}."},
        {"section": "Candidate questions", "minutes": 10, "prompt": "Capture questions, constraints, and follow-up commitments."},
        {"section": "Independent scorecard", "minutes": 5, "prompt": "Submit evidence before reviewing any other interviewer feedback."},
    ]
    return CapabilityResult(
        ok=True,
        output={"interview_id": interview.interview_id, "candidate_id": candidate.candidate_id, "agenda": agenda, "scorecard_ids": [item.scorecard_id for item in scorecards]},
        facts=["interview brief assembled from tenant-scoped ATS records", "no interview feedback or hiring decision was generated automatically"],
    )


async def cap_prepare_job_publication(
    inputs: dict[str, Any], ctx: CapabilityContext
) -> CapabilityResult:
    """Build a reviewable job-board packet; never publishes to a third party."""
    world: WorldState = ctx.world
    requisition = await world.get_requisition(ctx.organization_id, inputs["requisition_id"])
    if not requisition:
        return CapabilityResult(ok=False, error="requisition not found")
    boards = inputs.get("boards", ["internal_careers", "indeed", "linkedin", "jooble"])
    if not isinstance(boards, list) or not all(isinstance(board, str) for board in boards):
        return CapabilityResult(ok=False, error="boards must be a list of board identifiers")
    return CapabilityResult(
        ok=True,
        output={
            "requisition_id": requisition.requisition_id,
            "title": requisition.title,
            "location": requisition.location,
            "employment_type": requisition.employment_type,
            "headcount": requisition.headcount,
            "targets": boards,
            "external_publish_state": "draft_only",
        },
        facts=["job-board packet prepared without sending to any third party", "external publication requires a configured adapter and explicit human approval"],
    )


async def cap_triage_requisition(
    inputs: dict[str, Any], ctx: CapabilityContext
) -> CapabilityResult:
    """Surface reviewable recruiting blockers without changing records or sending messages."""
    world: WorldState = ctx.world
    requisition = await world.get_requisition(ctx.organization_id, inputs["requisition_id"])
    if not requisition:
        return CapabilityResult(ok=False, error="requisition not found")
    applications = await world.list_applications(ctx.organization_id, requisition_id=requisition.requisition_id)
    actions: list[dict[str, str]] = []
    for application in applications:
        if application.fit_score is None:
            actions.append({"priority": "high", "action": "score_application", "application_id": application.application_id, "reason": "fit score is missing"})
        elif application.current_stage_name.lower() in {"interview", "onsite"}:
            interviews = await world.list_interviews(ctx.organization_id, application_id=application.application_id)
            if not interviews:
                actions.append({"priority": "medium", "action": "schedule_interview", "application_id": application.application_id, "reason": "interview-stage application has no scheduled interview"})
    return CapabilityResult(
        ok=True,
        output={"requisition_id": requisition.requisition_id, "actions": actions[:50], "count": len(actions)},
        facts=["triage returns recommendations only; recruiters decide whether to plan and execute each follow-up"],
    )


async def _execute_retention_action(
    inputs: dict[str, Any], ctx: CapabilityContext, expected_action: str
) -> CapabilityResult:
    """Execute only the explicitly approved retention action through the runtime."""
    retention_case_id = str(inputs.get("retention_case_id", "")).strip()
    if not retention_case_id:
        return CapabilityResult(ok=False, error="retention_case_id is required")
    try:
        retention_case = await ctx.world.execute_retention_case(
            ctx.organization_id, retention_case_id, expected_action=expected_action
        )
    except ValueError as exc:
        return CapabilityResult(ok=False, error=str(exc))
    if not retention_case:
        return CapabilityResult(ok=False, error="retention case not found")
    return CapabilityResult(
        ok=True,
        output={
            "retention_case_id": retention_case.retention_case_id,
            "subject_type": retention_case.subject_type,
            "subject_id": retention_case.subject_id,
            "action": expected_action,
            "status": retention_case.status.value,
        },
        facts=[
            "retention action executed only after an approved non-held review case",
            "archive removes the subject from active operations; erasure redacts direct operational data while retaining minimum governance evidence",
        ],
    )


async def cap_execute_retention_archive(inputs: dict[str, Any], ctx: CapabilityContext) -> CapabilityResult:
    return await _execute_retention_action(inputs, ctx, "archive")


async def cap_execute_retention_erasure(inputs: dict[str, Any], ctx: CapabilityContext) -> CapabilityResult:
    return await _execute_retention_action(inputs, ctx, "erase")


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
    (
        CapabilitySpec(
            capability_id="cap.match_requisition",
            name="Match Requisition",
            description="Deterministically rank in-tenant prospects against requisition skills.",
            category="sourcing",
            inputs={"requisition_id": "str", "limit": "int?"},
            outputs={"matches": "list[Match]", "count": "int"},
            permissions=["world.requisitions.read", "world.candidates.read"],
        ),
        cap_match_requisition,
    ),
    (
        CapabilitySpec(
            capability_id="cap.source_requisition_prospects",
            name="Source Requisition Prospects",
            description="Create a consent-aware in-tenant prospect shortlist without contacting or changing candidates.",
            category="sourcing",
            inputs={"requisition_id": "str", "limit": "int?"},
            outputs={"prospects": "list[Prospect]", "count": "int"},
            permissions=["world.requisitions.read", "world.candidates.read", "world.consents.read"],
        ),
        cap_source_requisition_prospects,
    ),
    (
        CapabilitySpec(
            capability_id="cap.analyze_resume",
            name="Analyze Parsed Resume",
            description="Summarize parsed resume evidence without parsing files, scoring fit, or mutating candidate data.",
            category="screening",
            inputs={"candidate_id": "str", "resume_id": "str?"},
            outputs={"extracted_skills": "list[str]", "strengths": "list[str]", "limitations": "list[str]"},
            permissions=["world.candidates.read", "world.resumes.read"],
        ),
        cap_analyze_resume,
    ),
    (
        CapabilitySpec(
            capability_id="cap.score_application",
            name="Score Application",
            description="Persist explainable skill-fit analysis for one application.",
            category="screening",
            inputs={"application_id": "str"},
            outputs={"fit_score": "float", "matched_skills": "list[str]", "skill_gaps": "list[str]"},
            permissions=["world.applications.read", "world.applications.write", "world.candidates.read"],
        ),
        cap_score_application,
    ),
    (
        CapabilitySpec(
            capability_id="cap.prepare_interview",
            name="Prepare Interview",
            description="Prepare a grounded structured-interview brief without deciding outcomes.",
            category="interview",
            inputs={"interview_id": "str"},
            outputs={"agenda": "list[AgendaItem]", "scorecard_ids": "list[str]"},
            permissions=["world.interviews.read", "world.scorecards.read", "world.candidates.read"],
        ),
        cap_prepare_interview,
    ),
    (
        CapabilitySpec(
            capability_id="cap.prepare_job_publication",
            name="Prepare Job Publication",
            description="Create a reviewable job-distribution packet without publishing externally.",
            category="ops",
            sensitivity=Sensitivity.CONFIDENTIAL,
            inputs={"requisition_id": "str", "boards": "list[str]?"},
            outputs={"external_publish_state": "str", "targets": "list[str]"},
            permissions=["world.requisitions.read"],
        ),
        cap_prepare_job_publication,
    ),
    (
        CapabilitySpec(
            capability_id="cap.triage_requisition",
            name="Triage Requisition",
            description="Surface reviewable recruiting blockers without moving records or sending messages.",
            category="ops",
            inputs={"requisition_id": "str"},
            outputs={"actions": "list[TriageAction]", "count": "int"},
            permissions=["world.requisitions.read", "world.applications.read", "world.interviews.read"],
        ),
        cap_triage_requisition,
    ),
    (
        CapabilitySpec(
            capability_id="cap.execute_retention_archive",
            name="Execute Retention Archive",
            description="Archive an approved, non-held candidate or application retention case.",
            category="ops",
            sensitivity=Sensitivity.RESTRICTED,
            inputs={"retention_case_id": "str"},
            outputs={"retention_case_id": "str", "status": "str"},
            permissions=["world.retention.execute", "world.candidates.write", "world.applications.write"],
        ),
        cap_execute_retention_archive,
    ),
    (
        CapabilitySpec(
            capability_id="cap.execute_retention_erasure",
            name="Execute Retention Erasure",
            description="Redact approved, non-held candidate or application operational data while preserving minimum governance evidence.",
            category="ops",
            sensitivity=Sensitivity.RESTRICTED,
            inputs={"retention_case_id": "str"},
            outputs={"retention_case_id": "str", "status": "str"},
            permissions=["world.retention.execute", "world.candidates.write", "world.applications.write"],
        ),
        cap_execute_retention_erasure,
    ),
]


def build_default_registry() -> CapabilityRegistry:
    reg = CapabilityRegistry()
    for spec, handler in BUILTIN_CAPABILITIES:
        reg.register(spec, handler)
    return reg
