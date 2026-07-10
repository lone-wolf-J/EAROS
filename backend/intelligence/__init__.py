"""EAROS Intelligence Layer.

The company IP. Domain reasoning modules that operate on World State.
Every recommendation produced here MUST be explainable
(reasoning + confidence + evidence + tradeoffs).
"""
from __future__ import annotations

import os
from typing import Any, Optional

from foundation import (
    ConfidenceScore,
    Evidence,
    ReasoningStep,
    Recommendation,
)
from platform_core.world import Candidate, Job, PipelineStage, WorldState


# ============================================================
#   HIRING PLANNER — cross-objective candidate ranking
# ============================================================

async def hiring_recommendations_for_job(
    world: WorldState, organization_id: str, job_id: str, top_n: int = 5
) -> list[Recommendation]:
    """Rank candidates on a job across quality, speed, retention, team fit, and risk."""
    job = await world.get_job(job_id)
    if not job:
        return []
    candidates = await world.list_candidates(organization_id, job_id=job_id)
    if not candidates:
        return []

    scored: list[tuple[Candidate, dict[str, float], float]] = []
    for c in candidates:
        req = set(s.lower() for s in job.required_skills)
        have = set(s.lower() for s in c.skills)
        skill_overlap = len(req & have) / max(1, len(req))
        exp_fit = min(1.0, c.years_experience / 8.0)
        salary_fit = 1.0 - min(1.0, abs(c.expected_salary - (job.salary_min + job.salary_max) / 2)
                               / max(1, (job.salary_max - job.salary_min) / 2))
        location_fit = 1.0 if c.country == job.country else 0.7
        stage_bonus = {
            PipelineStage.SOURCED: 0.0, PipelineStage.SCREENING: 0.05,
            PipelineStage.PHONE_SCREEN: 0.1, PipelineStage.TECHNICAL: 0.15,
            PipelineStage.ONSITE: 0.2, PipelineStage.OFFER: 0.25,
            PipelineStage.HIRED: 0.0, PipelineStage.REJECTED: -0.5,
            PipelineStage.WITHDRAWN: -0.5,
        }.get(c.stage, 0.0)
        risk_penalty = 0.05 * len(c.risk_flags)

        composite = (
            0.40 * skill_overlap
            + 0.20 * exp_fit
            + 0.15 * salary_fit
            + 0.10 * location_fit
            + 0.15 * (0.5 + stage_bonus)
            - risk_penalty
        )
        composite = max(0.0, min(1.0, composite))
        scored.append((c, {
            "skill_overlap": round(skill_overlap, 3),
            "experience_fit": round(exp_fit, 3),
            "salary_fit": round(salary_fit, 3),
            "location_fit": round(location_fit, 3),
            "stage_bonus": round(stage_bonus, 3),
            "risk_penalty": round(risk_penalty, 3),
        }, composite))

    scored.sort(key=lambda x: -x[2])
    top = scored[:top_n]

    recs: list[Recommendation] = []
    for c, breakdown, score in top:
        req = set(s.lower() for s in job.required_skills)
        have = set(s.lower() for s in c.skills)
        overlap = sorted(req & have)
        missing = sorted(req - have)

        reasoning = [
            ReasoningStep(step=1,
                          thought=f"Skill coverage {breakdown['skill_overlap']:.0%} — matched: {', '.join(overlap) or 'none'}",
                          conclusion="Strong skill alignment." if breakdown['skill_overlap'] >= 0.6
                                     else "Skill gap present." if breakdown['skill_overlap'] < 0.4
                                     else "Partial skill alignment."),
            ReasoningStep(step=2,
                          thought=f"Experience fit {breakdown['experience_fit']:.2f} ({c.years_experience:.1f} yrs).",
                          conclusion="Level-appropriate." if breakdown['experience_fit'] >= 0.6 else "Under-seasoned."),
            ReasoningStep(step=3,
                          thought=f"Salary parity {breakdown['salary_fit']:.2f}; candidate expects "
                                  f"{c.currency} {c.expected_salary:,}, job band "
                                  f"{c.currency} {job.salary_min:,}–{job.salary_max:,}.",
                          conclusion="Budget-fit." if breakdown['salary_fit'] >= 0.6 else "Budget-stretch."),
            ReasoningStep(step=4,
                          thought=f"Composite score {score:.3f} weighted across skills, experience, salary, "
                                  f"location, current stage, and risk flags.",
                          conclusion="Recommend advance." if score >= 0.6
                                     else "Recommend hold." if score >= 0.45
                                     else "Recommend pass."),
        ]

        evidence = [
            Evidence(source="world.candidate", reference=c.candidate_id,
                     excerpt=f"{c.current_title} @ {c.current_company}, {c.years_experience:.1f} yrs"),
            Evidence(source="world.job", reference=job.job_id,
                     excerpt=f"{job.title} ({job.level}) in {job.location}"),
            Evidence(source="policy.parity",
                     reference="band",
                     excerpt=f"band mid = {(job.salary_min + job.salary_max) // 2}"),
        ]

        tradeoffs = []
        if missing:
            tradeoffs.append(f"Missing skills: {', '.join(missing[:5])}")
        if c.country != job.country:
            tradeoffs.append(f"Cross-border candidate: {c.country} -> {job.country}")
        if c.risk_flags:
            tradeoffs.append(f"Risk flags: {', '.join(c.risk_flags)}")

        risks = list(c.risk_flags)
        if breakdown["salary_fit"] < 0.5:
            risks.append("Compensation gap may cause drop-off")

        action = ("cap.advance_stage" if score >= 0.6
                  else "cap.screen_candidate" if score >= 0.45
                  else "cap.advance_stage")
        action_inputs: dict[str, Any] = (
            {"candidate_id": c.candidate_id, "stage": "phone_screen"} if score >= 0.6
            else {"candidate_id": c.candidate_id} if score >= 0.45
            else {"candidate_id": c.candidate_id, "stage": "rejected"}
        )

        recs.append(Recommendation(
            title=f"{c.full_name} — {c.current_title}",
            summary=(
                f"Composite fit {score:.3f} for {job.title}. "
                f"{'Recommend advance to phone screen.' if score >= 0.6 else 'Recommend deeper screen.' if score >= 0.45 else 'Recommend pass.'}"
            ),
            action=action,
            inputs=action_inputs,
            confidence=ConfidenceScore.from_value(0.5 + 0.5 * score),
            reasoning=reasoning,
            evidence=evidence,
            alternatives=[
                {"action": "cap.draft_outreach", "when": "not yet contacted",
                 "inputs": {"candidate_id": c.candidate_id}},
                {"action": "cap.schedule_interview", "when": "already screened",
                 "inputs": {"candidate_id": c.candidate_id, "stage": "phone_screen"}},
            ],
            tradeoffs=tradeoffs,
            risks=risks,
        ))
    return recs


# ============================================================
#   OFFER INTELLIGENCE
# ============================================================

async def offer_recommendation(
    world: WorldState, organization_id: str, candidate_id: str
) -> Optional[Recommendation]:
    cand = await world.get_candidate(candidate_id)
    if not cand:
        return None
    job = await world.get_job(cand.job_id)
    if not job:
        return None

    mid = (job.salary_min + job.salary_max) // 2
    # start from expected_salary anchored inside band
    expected = cand.expected_salary
    base = max(job.salary_min, min(job.salary_max, int(expected * 1.03)))
    if base < mid:
        base = int((base + mid) / 2)  # avoid low-ball
    bonus = int(base * 0.15)
    equity = 2500 if job.level in ("IC5", "M4", "M5", "VP") else 1500
    signing = int(base * 0.05)

    market_percentile = (base - job.salary_min) / max(1, job.salary_max - job.salary_min)
    parity_delta = (base - mid) / max(1, mid)
    acceptance = min(0.95, 0.55 + 0.35 * market_percentile
                     + (0.1 if cand.stage == PipelineStage.OFFER else 0.0))

    reasoning = [
        ReasoningStep(step=1, thought=f"Job band {job.currency} {job.salary_min:,}–{job.salary_max:,}, "
                                       f"midpoint {mid:,}."),
        ReasoningStep(step=2, thought=f"Candidate expectation {cand.currency} {expected:,}; "
                                       f"anchor at {base:,} (avoid low-ball, stay within band)."),
        ReasoningStep(step=3, thought=f"Estimated market percentile {market_percentile:.0%}, "
                                       f"parity delta vs. band-mid {parity_delta:+.2%}."),
        ReasoningStep(step=4, thought=f"Modeled acceptance probability {acceptance:.0%}.",
                      conclusion="Recommend extending offer."),
    ]
    evidence = [
        Evidence(source="world.job", reference=job.job_id,
                 excerpt=f"band {job.currency} {job.salary_min:,}–{job.salary_max:,}"),
        Evidence(source="world.candidate", reference=cand.candidate_id,
                 excerpt=f"expects {cand.currency} {expected:,}"),
        Evidence(source="policy.internal_parity", reference="band_mid",
                 excerpt=f"internal band-mid {mid:,}"),
    ]

    return Recommendation(
        title=f"Offer for {cand.full_name}",
        summary=f"Recommend {job.currency} base {base:,} + {bonus:,} bonus + {equity} equity units "
                f"+ signing {signing:,}. Acceptance ~ {acceptance:.0%}.",
        action="cap.generate_offer",
        inputs={
            "candidate_id": cand.candidate_id,
            "base_salary": base,
            "equity_units": equity,
            "signing_bonus": signing,
        },
        confidence=ConfidenceScore.from_value(0.5 + 0.4 * market_percentile),
        reasoning=reasoning,
        evidence=evidence,
        alternatives=[
            {"label": "Aggressive", "base": int(base * 1.08),
             "acceptance_estimate": round(min(0.97, acceptance + 0.1), 3)},
            {"label": "Conservative", "base": int(base * 0.95),
             "acceptance_estimate": round(max(0.3, acceptance - 0.15), 3)},
        ],
        tradeoffs=[
            f"Parity delta {parity_delta:+.2%} vs band-mid",
            f"Signing bonus {signing:,} adds first-year cost",
        ],
        risks=[
            "Counter-offer likely if base < 90% of expectation",
            "Cross-border tax treatment may adjust net" if cand.country != job.country else "",
        ],
    )


# ============================================================
#   ORGANIZATIONAL INTELLIGENCE
# ============================================================

async def organizational_health(
    world: WorldState, organization_id: str
) -> dict[str, Any]:
    departments = await world.list_departments(organization_id)
    teams = await world.list_teams(organization_id)
    jobs = await world.list_jobs(organization_id)
    open_jobs = [j for j in jobs if j.status.value == "open"]
    candidates = await world.list_candidates(organization_id)

    by_dept: dict[str, dict[str, Any]] = {}
    for d in departments:
        d_teams = [t for t in teams if t.department_id == d.department_id]
        d_open = sum(t.open_seats for t in d_teams)
        by_dept[d.name] = {
            "department_id": d.department_id,
            "headcount": d.headcount,
            "open_seats": d_open,
            "attrition_rate": d.attrition_rate,
            "health_score": d.health_score,
            "teams": len(d_teams),
        }

    stage_counts: dict[str, int] = {}
    for c in candidates:
        stage_counts[c.stage.value] = stage_counts.get(c.stage.value, 0) + 1

    return {
        "organization_id": organization_id,
        "total_departments": len(departments),
        "total_teams": len(teams),
        "total_open_reqs": len(open_jobs),
        "total_candidates": len(candidates),
        "by_department": by_dept,
        "pipeline_by_stage": stage_counts,
        "avg_attrition": round(sum(d.attrition_rate for d in departments) / max(1, len(departments)), 3),
        "avg_health_score": round(sum(d.health_score for d in departments) / max(1, len(departments)), 3),
    }


# ============================================================
#   WORKFORCE INTELLIGENCE (skill gaps)
# ============================================================

async def skill_gap_analysis(
    world: WorldState, organization_id: str
) -> list[dict[str, Any]]:
    jobs = await world.list_jobs(organization_id)
    open_jobs = [j for j in jobs if j.status.value == "open"]
    demand: dict[str, int] = {}
    for j in open_jobs:
        for s in j.required_skills:
            k = s.lower()
            demand[k] = demand.get(k, 0) + 1

    candidates = await world.list_candidates(organization_id)
    supply: dict[str, int] = {}
    for c in candidates:
        for s in c.skills:
            k = s.lower()
            supply[k] = supply.get(k, 0) + 1

    rows: list[dict[str, Any]] = []
    for skill, dem in sorted(demand.items(), key=lambda x: -x[1]):
        sup = supply.get(skill, 0)
        rows.append({
            "skill": skill,
            "demand": dem,
            "supply": sup,
            "gap": dem - sup,
            "scarcity": "critical" if sup == 0 else "high" if sup < dem else "healthy",
        })
    return rows


# ============================================================
#   STRATEGY INTELLIGENCE
# ============================================================

async def hiring_strategy(
    world: WorldState, organization_id: str
) -> Recommendation:
    jobs = await world.list_jobs(organization_id)
    open_jobs = [j for j in jobs if j.status.value == "open"]
    p0 = [j for j in open_jobs if j.priority == "P0"]
    p1 = [j for j in open_jobs if j.priority == "P1"]
    gaps = await skill_gap_analysis(world, organization_id)
    top_gaps = [g for g in gaps if g["scarcity"] in ("critical", "high")][:5]

    reasoning = [
        ReasoningStep(step=1,
                      thought=f"{len(open_jobs)} open reqs across the portfolio: "
                              f"{len(p0)} P0, {len(p1)} P1.",
                      conclusion="Concentrate on P0 first."),
        ReasoningStep(step=2,
                      thought=f"Top skill scarcities: {', '.join(g['skill'] for g in top_gaps) or 'none'}",
                      conclusion="Route sourcing capital to scarce skills."),
        ReasoningStep(step=3,
                      thought="Consider dual-track sourcing: outbound for scarce skills, "
                              "inbound (referral/agency) for volume roles.",
                      conclusion="Adopt hybrid channel strategy."),
    ]
    return Recommendation(
        title="Quarterly Hiring Strategy",
        summary=(f"Focus on {len(p0)} P0 roles; unlock scarcity in "
                 f"{', '.join(g['skill'] for g in top_gaps[:3]) or 'core skills'}; "
                 f"use hybrid channel mix."),
        action="human.review_strategy",
        inputs={"open_jobs": len(open_jobs)},
        confidence=ConfidenceScore.from_value(0.72),
        reasoning=reasoning,
        evidence=[
            Evidence(source="world.jobs", reference="open",
                     excerpt=f"{len(open_jobs)} open reqs"),
            Evidence(source="intelligence.skill_gap",
                     reference="top",
                     excerpt=str(top_gaps[:3])),
        ],
        tradeoffs=[
            "Outbound sourcing has higher cost-per-hire but shorter time-to-fill for scarce skills",
            "Referral bonuses inflate first-year cost but improve retention",
        ],
        risks=[
            "Salesforce/Dynamics talent scarcity may push offers above band mid",
            "Cross-border hires (India<->USA) add compliance overhead",
        ],
    )
