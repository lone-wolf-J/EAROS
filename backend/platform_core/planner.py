"""Planner — task decomposition + execution plans.

The Planner PROPOSES plans (with reasoning/confidence). It never executes.
Uses Claude Sonnet 4.5 via emergentintegrations; falls back to deterministic
templates when the LLM is unreachable.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from foundation import (
    ConfidenceScore,
    Evidence,
    ReasoningStep,
    Recommendation,
    Sensitivity,
    new_plan_id,
    utcnow_iso,
)
from platform_core.capabilities import CapabilityRegistry
from platform_core.runtime import PlanStep
from platform_core.world import Job, WorldState


class Plan(BaseModel):
    model_config = ConfigDict(extra="ignore")
    plan_id: str = Field(default_factory=new_plan_id)
    goal: str
    steps: list[PlanStep] = Field(default_factory=list)
    recommendation: Recommendation


PLANNER_SYSTEM = """You are the EAROS Hiring Planner. You produce structured execution plans; you NEVER execute.

You MUST return ONLY valid JSON matching this schema:
{
  "reasoning": [{"step": 1, "thought": "...", "conclusion": "..."}],
  "confidence": 0.0-1.0,
  "risks": ["..."],
  "tradeoffs": ["..."],
  "evidence": [{"source": "...", "reference": "...", "excerpt": "..."}],
  "steps": [
    {"capability_id": "cap.xxx", "inputs": {...}, "description": "...", "confidence": 0.0-1.0}
  ]
}

Available capabilities (use ONLY these IDs):
- cap.source_candidates(job_id, limit?)
- cap.screen_candidate(candidate_id)
- cap.advance_stage(candidate_id, stage) where stage in [sourced, screening, phone_screen, technical, onsite, offer, hired, rejected, withdrawn]
- cap.draft_outreach(candidate_id)
- cap.generate_offer(candidate_id, base_salary?, equity_units?, signing_bonus?)
- cap.schedule_interview(candidate_id, stage?, interviewer?, slot?)
- cap.match_requisition(requisition_id, limit?)
- cap.source_requisition_prospects(requisition_id, limit?)
- cap.analyze_resume(candidate_id, resume_id?)
- cap.score_application(application_id)
- cap.prepare_interview(interview_id)
- cap.prepare_job_publication(requisition_id, boards?)
- cap.triage_requisition(requisition_id)

Principles:
- Reason step-by-step against the world state facts provided.
- Prefer minimum viable plans.
- Only propose offer generation when candidate is at 'onsite' or later.
- Job publication capability creates a draft packet only; never claim an external board was published to.
- Interview preparation and workflow triage are recommendations only; never infer or submit hiring feedback.
- Resume analysis uses an already parsed profile only; it must not parse raw files, score an application, or alter a candidate.
- Sourcing and outreach drafts require active recorded recruiting consent and never contact candidates directly.
- If information is missing, propose the retrieval step first.
"""


class Planner:
    def __init__(self, world: WorldState, registry: CapabilityRegistry):
        self.world = world
        self.registry = registry
        self.llm_key = os.environ.get("EMERGENT_LLM_KEY", "")

    async def plan(
        self,
        goal: str,
        organization_id: str,
        context: dict[str, Any],
    ) -> Plan:
        # Gather world-state facts as grounding
        facts = await self._gather_facts(organization_id, context)
        llm_plan = await self._llm_plan(goal, facts, context)

        if llm_plan is None:
            # deterministic fallback
            llm_plan = self._fallback_plan(goal, context, facts)

        steps: list[PlanStep] = []
        for s in llm_plan.get("steps", []):
            cap_id = s.get("capability_id", "")
            if not self.registry.get_spec(cap_id):
                continue  # skip invalid capability ids the LLM might hallucinate
            steps.append(PlanStep(
                capability_id=cap_id,
                inputs=s.get("inputs", {}),
                description=s.get("description"),
                confidence=float(s.get("confidence", llm_plan.get("confidence", 0.75))),
                sensitivity=Sensitivity(s.get("sensitivity", "internal")),
            ))

        reasoning = [
            ReasoningStep(step=r.get("step", i + 1),
                          thought=r.get("thought", ""),
                          conclusion=r.get("conclusion"))
            for i, r in enumerate(llm_plan.get("reasoning", []))
        ]
        evidence = [
            Evidence(source=e.get("source", "world_state"),
                     reference=e.get("reference", ""),
                     excerpt=e.get("excerpt"))
            for e in llm_plan.get("evidence", [])
        ]

        rec = Recommendation(
            title=f"Plan: {goal}",
            summary=llm_plan.get("summary", goal),
            action="runtime.execute_plan",
            inputs={"steps": [s.model_dump() for s in steps]},
            confidence=ConfidenceScore.from_value(float(llm_plan.get("confidence", 0.7))),
            reasoning=reasoning,
            evidence=evidence,
            tradeoffs=llm_plan.get("tradeoffs", []),
            risks=llm_plan.get("risks", []),
        )
        return Plan(goal=goal, steps=steps, recommendation=rec)

    async def _gather_facts(
        self, organization_id: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        facts: dict[str, Any] = {"organization_id": organization_id, "gathered_at": utcnow_iso()}
        job_id = context.get("job_id")
        if job_id:
            job = await self.world.get_job_for_organization(organization_id, job_id)
            if job:
                facts["job"] = job.model_dump()
                cands = await self.world.list_candidates(organization_id, job_id=job_id)
                facts["candidates"] = [
                    {"candidate_id": c.candidate_id, "full_name": c.full_name,
                     "stage": c.stage.value, "fit_score": c.fit_score,
                     "years_experience": c.years_experience, "skills": c.skills[:6]}
                    for c in cands[:15]
                ]
        cand_id = context.get("candidate_id")
        if cand_id:
            c = await self.world.get_candidate_for_organization(organization_id, cand_id)
            if c:
                facts["candidate"] = c.model_dump()
                if not facts.get("job"):
                    j = await self.world.get_job_for_organization(organization_id, c.job_id)
                    if j:
                        facts["job"] = j.model_dump()
        requisition_id = context.get("requisition_id")
        if requisition_id:
            requisition = await self.world.get_requisition(organization_id, requisition_id)
            if requisition:
                facts["requisition"] = requisition.model_dump()
                facts["applications"] = [
                    application.model_dump()
                    for application in await self.world.list_applications(
                        organization_id, requisition_id=requisition_id
                    )
                ][:30]
        return facts

    async def _llm_plan(
        self, goal: str, facts: dict[str, Any], context: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        if not self.llm_key:
            return None
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
        except Exception:
            return None

        prompt = (
            f"GOAL: {goal}\n\n"
            f"CONTEXT: {json.dumps(context)[:2000]}\n\n"
            f"WORLD STATE FACTS:\n{json.dumps(facts, default=str)[:6000]}\n\n"
            "Return ONLY the JSON plan (no markdown fences)."
        )
        try:
            chat = LlmChat(
                api_key=self.llm_key,
                session_id=f"planner-{new_plan_id()}",
                system_message=PLANNER_SYSTEM,
            ).with_model("anthropic", "claude-sonnet-4-5-20250929")
            resp = await chat.send_message(UserMessage(text=prompt))
            text = resp if isinstance(resp, str) else getattr(resp, "content", str(resp))
            return _extract_json(text)
        except Exception:
            return None

    def _fallback_plan(
        self, goal: str, context: dict[str, Any], facts: dict[str, Any]
    ) -> dict[str, Any]:
        job_id = context.get("job_id") or (facts.get("job") or {}).get("job_id")
        candidate_id = context.get("candidate_id")
        requisition_id = context.get("requisition_id")
        application_id = context.get("application_id")
        interview_id = context.get("interview_id")
        steps: list[dict[str, Any]] = []
        reasoning: list[dict[str, Any]] = []

        goal_low = goal.lower()
        if "resume" in goal_low and ("analysis" in goal_low or "analy" in goal_low) and candidate_id:
            steps = [{
                "capability_id": "cap.analyze_resume",
                "inputs": {"candidate_id": candidate_id},
                "description": "Summarize stored parsed-resume evidence for recruiter review.",
                "confidence": 0.78,
            }]
            reasoning = [{
                "step": 1, "thought": "Resume analysis is bounded to persisted parsed profile facts and does not mutate records.",
                "conclusion": "Invoke cap.analyze_resume under policy control."
            }]
        elif "score" in goal_low and application_id:
            steps = [{
                "capability_id": "cap.score_application",
                "inputs": {"application_id": application_id},
                "description": "Persist an explainable application fit score.",
                "confidence": 0.82,
            }]
            reasoning = [{
                "step": 1, "thought": "Application scoring is deterministic against requisition requirements.",
                "conclusion": "Invoke cap.score_application under policy control."
            }]
        elif "match" in goal_low and requisition_id:
            steps = [{
                "capability_id": "cap.match_requisition",
                "inputs": {"requisition_id": requisition_id, "limit": 20},
                "description": "Rank tenant prospects against the requisition skill requirements.",
                "confidence": 0.78,
            }]
            reasoning = [{
                "step": 1, "thought": "Prospect matching can be a read-only deterministic comparison.",
                "conclusion": "Invoke cap.match_requisition without altering candidate state."
            }]
        elif ("source" in goal_low or "prospect" in goal_low) and requisition_id:
            steps = [{
                "capability_id": "cap.source_requisition_prospects",
                "inputs": {"requisition_id": requisition_id, "limit": 20},
                "description": "Produce a consent-aware prospect shortlist for recruiter review.",
                "confidence": 0.76,
            }]
            reasoning = [{
                "step": 1, "thought": "Sourcing is limited to active in-tenant prospects with recorded recruiting consent.",
                "conclusion": "Invoke cap.source_requisition_prospects without contacting or mutating candidates."
            }]
        elif "publication" in goal_low and requisition_id:
            steps = [{
                "capability_id": "cap.prepare_job_publication",
                "inputs": {"requisition_id": requisition_id},
                "description": "Prepare a reviewable job-distribution packet.",
                "confidence": 0.8, "sensitivity": "confidential",
            }]
            reasoning = [{
                "step": 1, "thought": "No board adapter is allowed to publish from a plan.",
                "conclusion": "Prepare a draft packet for human review only."
            }]
        elif "triage" in goal_low and requisition_id:
            steps = [{
                "capability_id": "cap.triage_requisition",
                "inputs": {"requisition_id": requisition_id},
                "description": "Surface missing scores and interview scheduling blockers.",
                "confidence": 0.8,
            }]
            reasoning = [{
                "step": 1, "thought": "Workflow triage should surface facts without automating stage movement.",
                "conclusion": "Invoke cap.triage_requisition as a recommendation."
            }]
        elif "interview prep" in goal_low and interview_id:
            steps = [{
                "capability_id": "cap.prepare_interview",
                "inputs": {"interview_id": interview_id},
                "description": "Build a structured, evidence-oriented interview brief.",
                "confidence": 0.8,
            }]
            reasoning = [{
                "step": 1, "thought": "Interview preparation is grounded in tenant records and scorecards.",
                "conclusion": "Invoke cap.prepare_interview without generating feedback."
            }]
        elif "screen" in goal_low and candidate_id:
            steps = [{
                "capability_id": "cap.screen_candidate",
                "inputs": {"candidate_id": candidate_id},
                "description": "Deterministic screen against job requirements.",
                "confidence": 0.82,
            }]
            reasoning = [
                {"step": 1, "thought": "Screening is deterministic; single step suffices.",
                 "conclusion": "Invoke cap.screen_candidate."}
            ]
        elif "offer" in goal_low and candidate_id:
            steps = [{
                "capability_id": "cap.generate_offer",
                "inputs": {"candidate_id": candidate_id},
                "description": "Compose offer package with parity + market checks.",
                "confidence": 0.7, "sensitivity": "confidential",
            }]
            reasoning = [
                {"step": 1, "thought": "Offer generation is a sensitive single-step capability.",
                 "conclusion": "Invoke cap.generate_offer under confidential policy."}
            ]
        elif "outreach" in goal_low and candidate_id:
            steps = [{
                "capability_id": "cap.draft_outreach",
                "inputs": {"candidate_id": candidate_id},
                "description": "Draft candidate outreach.",
                "confidence": 0.78,
            }]
            reasoning = [
                {"step": 1, "thought": "Outreach is a deterministic templated draft.",
                 "conclusion": "Invoke cap.draft_outreach."}
            ]
        elif "source" in goal_low and job_id:
            steps = [{
                "capability_id": "cap.source_candidates",
                "inputs": {"job_id": job_id, "limit": 10},
                "description": "Source candidates from world state pool.",
                "confidence": 0.75,
            }]
            reasoning = [
                {"step": 1, "thought": "Sourcing is a deterministic filter over world state.",
                 "conclusion": "Invoke cap.source_candidates."}
            ]
        else:
            reasoning = [
                {"step": 1, "thought": "Goal did not match known patterns; returning empty plan.",
                 "conclusion": "No steps proposed."}
            ]

        return {
            "summary": f"Deterministic fallback plan for goal: {goal}",
            "confidence": 0.6 if steps else 0.2,
            "reasoning": reasoning,
            "risks": ["LLM unavailable — used deterministic fallback"] if not self.llm_key else [],
            "tradeoffs": ["Fallback plans are minimal; consider retrying when LLM is available."],
            "evidence": [{"source": "world_state", "reference": job_id or candidate_id or "-",
                          "excerpt": "grounded in current world state"}],
            "steps": steps,
        }


def _extract_json(text: str) -> Optional[dict[str, Any]]:
    if not text:
        return None
    # Strip markdown fences
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    # Find first { ... } balanced-ish
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start:end + 1])
    except Exception:
        return None
