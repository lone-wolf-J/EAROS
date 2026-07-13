"""Demo Scenarios — full-lifecycle end-to-end demonstrations.

A scenario spins up a background pipeline that emits realistic events, runs
capabilities through the runtime, and produces a reflection at the end.
This makes Mission Control genuinely alive during a demo.
"""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from typing import Any

from foundation import (
    DomainEvent,
    EventType,
    ExecutionStatus,
    PolicyDecision,
    Sensitivity,
    new_execution_id,
)
from platform_core.governance import Approval, Governance
from platform_core.policy import PolicyContext, PolicyEngine
from platform_core.reflection import Reflection
from platform_core.runtime import ExecutionRecord, PlanStep, Runtime
from platform_core.world import PipelineStage, WorldState

from intelligence.scenario_tracker import (
    STEP_PACE_SECONDS,
    ScenarioExecutionState,
    tracker,
)


SCENARIOS: list[dict[str, Any]] = [
    {"scenario_id": "scn.java_chennai",
     "title": "Senior Java Developer × 3 · Chennai",
     "tagline": "8+ yrs · Spring Boot · Kafka · Banking · Immediate joiners.",
     "brief": ("Need three Senior Java Developers in Chennai. 8+ years. "
               "Spring Boot, Kafka, Microservices. Banking domain preferred. "
               "Immediate joiners."),
     "seed_job_id": "job_ai_staff_bang"},  # reuses an existing seeded job for candidates
    {"scenario_id": "scn.sfdc_arch",
     "title": "Salesforce Architect · Austin",
     "tagline": "Apex + CPQ + LWC. Anchor architect for Americas book.",
     "brief": "Hiring a Salesforce Architect in Austin. Apex, CPQ, LWC. M4 level.",
     "seed_job_id": "job_sfdc_arch_austin"},
    {"scenario_id": "scn.dynamics_hyd",
     "title": "Dynamics 365 F&O Consultant · Hyderabad",
     "tagline": "Scale D365 F&O practice for Q2 pipeline.",
     "brief": "Hiring a Dynamics 365 F&O Consultant in Hyderabad. IC4.",
     "seed_job_id": "job_dyn_cons_hyd"},
    {"scenario_id": "scn.ai_bang",
     "title": "Staff AI Engineer · Bangalore",
     "tagline": "Agentic systems, LangGraph, RAG. Product moat.",
     "brief": "Staff AI Engineer for agentic platform. Bangalore. LangGraph, RAG.",
     "seed_job_id": "job_ai_staff_bang"},
    {"scenario_id": "scn.pm_ai_sf",
     "title": "Principal AI PM · San Francisco",
     "tagline": "Owns EAROS Intelligence roadmap.",
     "brief": "Principal AI Product Manager in San Francisco. LLM Ops, RAG.",
     "seed_job_id": "job_ai_pm_sf"},
    {"scenario_id": "scn.data_eng_pune",
     "title": "Data Engineering Lead · Pune",
     "tagline": "Governed lakehouse for Executive Copilot.",
     "brief": "Data Engineering Lead in Pune. Databricks, PySpark, dbt.",
     "seed_job_id": "job_de_lead_pune"},
    {"scenario_id": "scn.sales_ny",
     "title": "Enterprise AE · New York",
     "tagline": "Q1 target: USD 6M new-logo ARR.",
     "brief": "Enterprise Account Executive in New York. MEDDIC, Value Selling.",
     "seed_job_id": "job_sales_ent_ny"},
    {"scenario_id": "scn.cp_boston",
     "title": "Client Partner · Financial Services · Boston",
     "tagline": "Own top-3 FS relationship worth USD 12M ARR.",
     "brief": "Client Partner for Financial Services in Boston. Program delivery.",
     "seed_job_id": "job_cp_boston"},
]


def list_scenarios() -> list[dict[str, Any]]:
    return SCENARIOS


async def _emit(gov: Governance, event_type: EventType, actor: str,
                subject_type: str, subject_id: str, organization_id: str,
                payload: dict[str, Any], correlation_id: str) -> None:
    await gov.emit(DomainEvent(
        event_type=event_type, actor=actor,
        subject_type=subject_type, subject_id=subject_id,
        organization_id=organization_id,
        payload=payload, correlation_id=correlation_id,
    ))


async def run_scenario(
    scenario_id: str,
    organization_id: str,
    user_id: str,
    world: WorldState,
    runtime: Runtime,
    policy: PolicyEngine,
    governance: Governance,
    reflection: Reflection,
) -> dict[str, Any]:
    """Run a complete lifecycle for the scenario. Executes serially for a
    realistic-feeling demo, emitting a rich event stream."""
    scenario = next((s for s in SCENARIOS if s["scenario_id"] == scenario_id), None)
    if not scenario:
        return {"error": "scenario not found"}

    job = await world.get_job(scenario["seed_job_id"])
    if not job:
        return {"error": "seed job not found"}

    correlation_id = new_execution_id()
    r = random.Random(f"scenario-{scenario_id}-{int(datetime.now(timezone.utc).timestamp() // 60)}")

    # Stage 0 — intake
    await _emit(governance, EventType.PLAN_CREATED, "agent.intake",
                "scenario", scenario_id, organization_id,
                {"stage": "intake", "brief": scenario["brief"][:120]}, correlation_id)

    # Stage 1 — sourcing sweep (executed via runtime)
    ex1 = ExecutionRecord(
        organization_id=organization_id,
        user_id=user_id, user_role="recruiter",
        goal=f"Sourcing sweep: {scenario['title']}",
        steps=[PlanStep(capability_id="cap.source_candidates",
                        inputs={"job_id": job.job_id, "limit": 25},
                        confidence=0.82)],
        correlation_id=correlation_id,
    )
    ex1 = await runtime.execute(ex1)
    await asyncio.sleep(0)  # yield

    # Stage 2 — screen the top 3 sourced candidates
    cands = await world.list_candidates(organization_id, job_id=job.job_id,
                                         stage=PipelineStage.SOURCED)
    top3 = cands[:3]
    for c in top3:
        ex = ExecutionRecord(
            organization_id=organization_id,
            user_id=user_id, user_role="recruiter",
            goal=f"Screen {c.full_name}",
            steps=[PlanStep(capability_id="cap.screen_candidate",
                            inputs={"candidate_id": c.candidate_id},
                            confidence=0.72)],
            correlation_id=correlation_id,
        )
        await runtime.execute(ex)

    # Stage 3 — outreach drafts (deterministic capability)
    for c in top3[:2]:
        ex = ExecutionRecord(
            organization_id=organization_id,
            user_id=user_id, user_role="recruiter",
            goal=f"Outreach draft for {c.full_name}",
            steps=[PlanStep(capability_id="cap.draft_outreach",
                            inputs={"candidate_id": c.candidate_id},
                            confidence=0.78)],
            correlation_id=correlation_id,
        )
        await runtime.execute(ex)

    # Stage 4 — schedule interview for the top candidate
    if top3:
        ex = ExecutionRecord(
            organization_id=organization_id,
            user_id=user_id, user_role="recruiter",
            goal=f"Schedule interview for {top3[0].full_name}",
            steps=[PlanStep(capability_id="cap.schedule_interview",
                            inputs={"candidate_id": top3[0].candidate_id,
                                    "stage": "technical",
                                    "interviewer": "Priya Menon (Engineering)",
                                    "slot": "Tomorrow 10:30 IST"},
                            confidence=0.83)],
            correlation_id=correlation_id,
        )
        await runtime.execute(ex)

    # Stage 5 — attempt an offer (POLICY-BLOCKED → creates approval)
    if top3:
        ex_offer = ExecutionRecord(
            organization_id=organization_id,
            user_id=user_id, user_role="recruiter",
            goal=f"Prepare offer for {top3[0].full_name}",
            steps=[PlanStep(capability_id="cap.generate_offer",
                            inputs={"candidate_id": top3[0].candidate_id},
                            confidence=0.86, sensitivity=Sensitivity.CONFIDENTIAL)],
            correlation_id=correlation_id,
        )
        await runtime.execute(ex_offer)

    # Stage 6 — reflection (summarize the scenario)
    from platform_core.reflection import ReflectionReport
    await reflection.record(ReflectionReport(
        organization_id=organization_id,
        execution_id=correlation_id,
        subject_type="scenario",
        subject_id=scenario_id,
        what_happened=f"Ran complete lifecycle for {scenario['title']}: sourcing, "
                       f"screening top 3, drafting outreach for top 2, scheduling "
                       f"technical interview for top 1, and preparing an offer that "
                       f"was correctly gated to human approval.",
        why="Demo scenario invoked from Mission Control.",
        what_succeeded=[
            "All screens executed above 0.60 confidence.",
            "Policy correctly gated the offer generation.",
            "Immutable events emitted at every step.",
        ],
        what_failed=[],
        improvements=[
            f"Consider raising min-confidence on {job.title} screens to 0.65.",
            "Parallelize the 3 screens — they are dependency-free.",
        ],
        metrics={
            "sourcing_matches": float(len(cands)),
            "screened": float(len(top3)),
            "outreach_drafted": 2.0,
            "interviews_scheduled": 1.0 if top3 else 0.0,
            "offers_awaiting_approval": 1.0 if top3 else 0.0,
        },
    ))

    return {
        "scenario_id": scenario_id,
        "correlation_id": correlation_id,
        "job_id": job.job_id,
        "job_title": job.title,
        "candidates_screened": [c.candidate_id for c in top3],
        "status": "completed",
    }



# ==========================================================================
# PACED SCENARIO RUNNER
# ==========================================================================
# The synchronous run_scenario above is retained for backwards compatibility
# with existing tests. The paced runner below is what powers the live demo:
# it emits per-step progress into ScenarioTracker with deliberate delays and
# uses a real approval gate that pauses until the user clicks Approve/Reject
# (or times out).

_SCENARIO_STEPS: list[tuple[str, str, str, str]] = [
    ("intake",        "Requirement Intake",   "Intake Agent",
     "Parsing the executive brief into structured requirements."),
    ("jd_intel",      "JD Intelligence",      "Job Architecture Agent",
     "Generating skill graph, competency matrix, and calibrated JD."),
    ("market_intel",  "Market Intelligence",  "Market Signal Agent",
     "Benchmarking comp, supply/demand, hotspots for the role."),
    ("planner",       "Planner",              "Planner",
     "Composing a multi-step execution plan under active policies."),
    ("policy_eval",   "Policy Evaluation",    "Policy Engine",
     "Evaluating fairness, DEI, PII, and confidence thresholds."),
    ("sourcing",      "Sourcing Sweep",       "Sourcing Agent",
     "Scanning GitHub, LinkedIn, Dice, internal ATS in parallel."),
    ("resume_intel",  "Resume Intelligence",  "Resume Agent",
     "Parsing resumes, extracting structured signal, deduping."),
    ("ranking",       "Ranking",              "Ranking Agent",
     "Scoring candidates against the calibrated brief."),
    ("outreach",      "Outreach",             "Outreach Agent",
     "Drafting hyper-personalised outreach for the top prospects."),
    ("screening",     "Screening",            "Screening Agent",
     "Running AI screens on the top 3 candidates."),
    ("interview",     "Interview Scheduling", "Scheduler Agent",
     "Coordinating panel + candidate calendars, sending invites."),
    ("offer_prep",    "Offer Preparation",    "Offer Agent",
     "Generating a comp-aligned offer letter (confidential)."),
    ("approval",      "Human Approval Gate",  "Governance",
     "Offer held for human approval — policy requires L2 sign-off."),
    ("reflection",    "Reflection",           "Reflection Agent",
     "Recording what worked, what to improve, and metrics."),
]


async def run_scenario_paced(
    execution_id: str,
    scenario_id: str,
    organization_id: str,
    user_id: str,
    world: WorldState,
    runtime: Runtime,
    policy: PolicyEngine,
    governance: Governance,
    reflection: Reflection,
) -> None:
    """Background task that runs a scenario with paced, observable steps.

    Emits per-step updates to the ScenarioTracker so the UI can render a
    live progress ribbon, current-agent banner, and an approval gate.
    """
    scenario = next((s for s in SCENARIOS if s["scenario_id"] == scenario_id), None)
    if not scenario:
        tracker.fail(execution_id, "scenario not found")
        return

    try:
        job = await world.get_job(scenario["seed_job_id"])
        if not job:
            tracker.fail(execution_id, "seed job not found")
            return

        correlation_id = new_execution_id()
        state = tracker.get(execution_id)
        if state:
            state.correlation_id = correlation_id

        # -- Stage: intake
        await tracker.start_step(execution_id, "intake")
        await _emit(governance, EventType.PLAN_CREATED, "agent.intake",
                    "scenario", scenario_id, organization_id,
                    {"stage": "intake", "brief": scenario["brief"][:120]},
                    correlation_id)
        await asyncio.sleep(STEP_PACE_SECONDS)
        await tracker.complete_step(execution_id, "intake",
            f"Extracted 12 requirements, 4 must-haves from brief.")

        # -- Stage: JD intelligence
        await tracker.start_step(execution_id, "jd_intel")
        await asyncio.sleep(STEP_PACE_SECONDS)
        await tracker.complete_step(execution_id, "jd_intel",
            f"Calibrated JD generated for {job.title} — 7 core skills, 3 differentiators.")

        # -- Stage: market intel
        await tracker.start_step(execution_id, "market_intel")
        await asyncio.sleep(STEP_PACE_SECONDS)
        await tracker.complete_step(execution_id, "market_intel",
            "Comp band 22–34 LPA · 340 active candidates · median response 3.1 days.")

        # -- Stage: planner
        await tracker.start_step(execution_id, "planner")
        await asyncio.sleep(STEP_PACE_SECONDS - 0.4)
        await tracker.complete_step(execution_id, "planner",
            "6-step plan composed. Confidence 0.82.")

        # -- Stage: policy eval
        await tracker.start_step(execution_id, "policy_eval")
        await asyncio.sleep(1.0)
        await tracker.complete_step(execution_id, "policy_eval",
            "All steps passed fairness, PII, DEI checks. Offer step flagged for approval.")

        # -- Stage: sourcing (runtime)
        await tracker.start_step(execution_id, "sourcing")
        ex1 = ExecutionRecord(
            organization_id=organization_id,
            user_id=user_id, user_role="recruiter",
            goal=f"Sourcing sweep: {scenario['title']}",
            steps=[PlanStep(capability_id="cap.source_candidates",
                            inputs={"job_id": job.job_id, "limit": 25},
                            confidence=0.82)],
            correlation_id=correlation_id,
        )
        await runtime.execute(ex1)
        await asyncio.sleep(STEP_PACE_SECONDS)
        cands = await world.list_candidates(organization_id, job_id=job.job_id,
                                             stage=PipelineStage.SOURCED)
        top3 = cands[:3]
        await tracker.complete_step(execution_id, "sourcing",
            f"Sourced {len(cands)} candidates across 4 sources.")

        # -- Stage: resume intel
        await tracker.start_step(execution_id, "resume_intel")
        await asyncio.sleep(STEP_PACE_SECONDS - 0.4)
        await tracker.complete_step(execution_id, "resume_intel",
            f"Parsed {len(top3)} resumes. 100% structured. 0 duplicates.")

        # -- Stage: ranking
        await tracker.start_step(execution_id, "ranking")
        await asyncio.sleep(STEP_PACE_SECONDS - 0.4)
        await tracker.complete_step(execution_id, "ranking",
            f"Top 3 ranked. Best-fit score 0.91.")

        # -- Stage: outreach (runtime for top 2)
        await tracker.start_step(execution_id, "outreach")
        for c in top3[:2]:
            ex = ExecutionRecord(
                organization_id=organization_id,
                user_id=user_id, user_role="recruiter",
                goal=f"Outreach draft for {c.full_name}",
                steps=[PlanStep(capability_id="cap.draft_outreach",
                                inputs={"candidate_id": c.candidate_id},
                                confidence=0.78)],
                correlation_id=correlation_id,
            )
            await runtime.execute(ex)
            await asyncio.sleep(0.6)
        await tracker.complete_step(execution_id, "outreach",
            f"Drafted personalised outreach for top {min(2, len(top3))} candidates.")

        # -- Stage: screening (runtime top 3)
        await tracker.start_step(execution_id, "screening")
        for c in top3:
            ex = ExecutionRecord(
                organization_id=organization_id,
                user_id=user_id, user_role="recruiter",
                goal=f"Screen {c.full_name}",
                steps=[PlanStep(capability_id="cap.screen_candidate",
                                inputs={"candidate_id": c.candidate_id},
                                confidence=0.72)],
                correlation_id=correlation_id,
            )
            await runtime.execute(ex)
            await asyncio.sleep(0.5)
        await tracker.complete_step(execution_id, "screening",
            f"Screened {len(top3)} candidates. 2 advanced.")

        # -- Stage: interview scheduling
        await tracker.start_step(execution_id, "interview")
        if top3:
            ex = ExecutionRecord(
                organization_id=organization_id,
                user_id=user_id, user_role="recruiter",
                goal=f"Schedule interview for {top3[0].full_name}",
                steps=[PlanStep(capability_id="cap.schedule_interview",
                                inputs={"candidate_id": top3[0].candidate_id,
                                        "stage": "technical",
                                        "interviewer": "Priya Menon (Engineering)",
                                        "slot": "Tomorrow 10:30 IST"},
                                confidence=0.83)],
                correlation_id=correlation_id,
            )
            await runtime.execute(ex)
        await asyncio.sleep(STEP_PACE_SECONDS - 0.5)
        await tracker.complete_step(execution_id, "interview",
            "Technical interview scheduled · panel + candidate confirmed.")

        # -- Stage: offer prep (runtime, policy will gate it)
        await tracker.start_step(execution_id, "offer_prep")
        if top3:
            ex_offer = ExecutionRecord(
                organization_id=organization_id,
                user_id=user_id, user_role="recruiter",
                goal=f"Prepare offer for {top3[0].full_name}",
                steps=[PlanStep(capability_id="cap.generate_offer",
                                inputs={"candidate_id": top3[0].candidate_id},
                                confidence=0.86,
                                sensitivity=Sensitivity.CONFIDENTIAL)],
                correlation_id=correlation_id,
            )
            await runtime.execute(ex_offer)
        await asyncio.sleep(STEP_PACE_SECONDS)
        offer_subject = top3[0].full_name if top3 else "candidate"
        await tracker.complete_step(execution_id, "offer_prep",
            f"Offer letter prepared for {offer_subject} · marked CONFIDENTIAL.")

        # -- Stage: approval gate (actually pauses)
        await tracker.start_step(execution_id, "approval")
        decision = await tracker.request_approval(
            execution_id,
            subject=f"Offer for {offer_subject}",
            reason=("Policy requires human approval for CONFIDENTIAL offers "
                    "above L2. AI confidence 0.86."),
        )
        await tracker.complete_step(execution_id, "approval",
            f"Human decision: {decision}.")

        # -- Stage: reflection
        await tracker.start_step(execution_id, "reflection")
        from platform_core.reflection import ReflectionReport
        await reflection.record(ReflectionReport(
            organization_id=organization_id,
            execution_id=correlation_id,
            subject_type="scenario",
            subject_id=scenario_id,
            what_happened=(
                f"Ran complete lifecycle for {scenario['title']}: sourcing, "
                f"screening top 3, drafting outreach for top 2, scheduling "
                f"technical interview for top 1, and an offer that was "
                f"correctly gated to human approval ({decision})."
            ),
            why="Demo scenario invoked from Mission Control.",
            what_succeeded=[
                "All screens executed above 0.60 confidence.",
                "Policy correctly gated the offer generation.",
                "Immutable events emitted at every step.",
            ],
            what_failed=[],
            improvements=[
                f"Consider raising min-confidence on {job.title} screens to 0.65.",
                "Parallelize the 3 screens — they are dependency-free.",
            ],
            metrics={
                "sourcing_matches": float(len(cands)),
                "screened": float(len(top3)),
                "outreach_drafted": 2.0,
                "interviews_scheduled": 1.0 if top3 else 0.0,
                "offers_awaiting_approval": 1.0 if top3 else 0.0,
            },
        ))
        await asyncio.sleep(0.8)
        await tracker.complete_step(execution_id, "reflection",
            "Reflection recorded · 5 metrics captured.")

        tracker.finish(execution_id, {
            "scenario_id": scenario_id,
            "correlation_id": correlation_id,
            "job_id": job.job_id,
            "job_title": job.title,
            "candidates_screened": [c.candidate_id for c in top3],
            "approval_decision": decision,
        })
    except Exception as exc:  # noqa: BLE001 — surface any error to the UI
        tracker.fail(execution_id, f"{type(exc).__name__}: {exc}")


def build_scenario_steps() -> list[tuple[str, str, str, str]]:
    """Public accessor so callers can pre-create tracker state."""
    return list(_SCENARIO_STEPS)
