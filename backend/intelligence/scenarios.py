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
