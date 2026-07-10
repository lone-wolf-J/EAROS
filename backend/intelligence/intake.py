"""Intake Intelligence — conversational requirements gathering.

Takes a free-text hiring brief and produces:
- Structured requirements (must-haves, nice-to-haves, band, location, timeline)
- Ambiguities + clarifying questions
- Recommended interview panel
- Sourcing channel recommendations
- Estimated difficulty + time-to-fill
- Compensation estimate
- Hiring risks
- Generated JD
- Screening rubric
- Confidence + assumptions
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

from foundation import (
    ConfidenceScore,
    Evidence,
    ReasoningStep,
    Recommendation,
)


INTAKE_SYSTEM = """You are the EAROS Hiring Intake Agent.

Given a hiring manager's free-text brief, return ONLY valid JSON in this schema:
{
  "role_title": "string",
  "level": "IC3|IC4|IC5|M4|M5|VP",
  "location": "string",
  "country": "India|USA|Other",
  "headcount": integer,
  "must_have_skills": ["..."],
  "nice_to_have_skills": ["..."],
  "domain_experience": ["..."],
  "seniority_years_min": integer,
  "seniority_years_max": integer,
  "employment_type": "Full-time|Contract|Contract-to-hire",
  "compensation_estimate_low": integer,
  "compensation_estimate_high": integer,
  "compensation_currency": "USD|INR",
  "urgency": "immediate|30_days|60_days|standard",
  "expected_time_to_fill_days": integer,
  "difficulty_score": 0.0-1.0,
  "hiring_risks": ["..."],
  "assumptions_made": ["..."],
  "ambiguities": ["..."],
  "clarifying_questions": ["..."],
  "recommended_interview_panel": [{"role": "...", "why": "..."}],
  "recommended_sourcing_channels": [{"channel": "LinkedIn|Dice|GitHub|Referrals|Internal ATS|Community|Naukri|Monster|Indeed", "why": "...", "priority": "P0|P1|P2"}],
  "generated_jd": {
    "title": "string",
    "one_liner": "string",
    "responsibilities": ["..."],
    "requirements": ["..."],
    "nice_to_have": ["..."],
    "team_context": "string",
    "growth_path": "string"
  },
  "screening_rubric": [
    {"dimension": "Technical", "weight": 0-1, "criteria": ["..."]},
    {"dimension": "Communication", "weight": 0-1, "criteria": ["..."]},
    {"dimension": "Leadership", "weight": 0-1, "criteria": ["..."]},
    {"dimension": "Culture", "weight": 0-1, "criteria": ["..."]},
    {"dimension": "Problem Solving", "weight": 0-1, "criteria": ["..."]},
    {"dimension": "Domain", "weight": 0-1, "criteria": ["..."]},
    {"dimension": "Motivation", "weight": 0-1, "criteria": ["..."]},
    {"dimension": "Availability", "weight": 0-1, "criteria": ["..."]}
  ],
  "confidence": 0.0-1.0,
  "reasoning_summary": "1-2 sentences explaining the biggest calls"
}

Rules:
- If the brief is vague about geography, prefer India for INR figures and USA for USD figures.
- Compensation should be in the currency implied by the location.
- Difficulty above 0.7 signals a scarce-skill role.
- Never invent hard commitments; if unclear, put it in `ambiguities` and `clarifying_questions`.
"""


DEFAULT_BRIEF = ("Hiring 3 Senior Java Developers in Chennai. 8+ years. Spring Boot, Kafka, "
                 "Microservices, Banking domain. Immediate joiners.")


def _extract_json(text: str) -> Optional[dict[str, Any]]:
    if not text:
        return None
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start:end + 1])
    except Exception:
        return None


def _fallback_intake(brief: str) -> dict[str, Any]:
    is_india = any(x in brief.lower() for x in ("india", "bangalore", "chennai",
                                                 "hyderabad", "pune", "mumbai",
                                                 "gurgaon", "inr"))
    location_hint = "Chennai, India" if is_india else "New York, USA"
    currency = "INR" if is_india else "USD"
    n = 1
    m = re.search(r"(\d+)\s+(senior|sr|lead|staff|principal)?\s*", brief.lower())
    if m:
        try:
            n = max(1, min(20, int(m.group(1))))
        except Exception:
            n = 1
    return {
        "role_title": "Senior Java Developer" if "java" in brief.lower()
                      else "Senior Engineer",
        "level": "IC4",
        "location": location_hint,
        "country": "India" if is_india else "USA",
        "headcount": n,
        "must_have_skills": ["Java", "Spring Boot", "Microservices"],
        "nice_to_have_skills": ["Kafka", "Kubernetes"],
        "domain_experience": ["Banking"] if "bank" in brief.lower() else [],
        "seniority_years_min": 8,
        "seniority_years_max": 12,
        "employment_type": "Full-time",
        "compensation_estimate_low": 2200000 if is_india else 150000,
        "compensation_estimate_high": 3400000 if is_india else 200000,
        "compensation_currency": currency,
        "urgency": "immediate" if "immediate" in brief.lower() else "30_days",
        "expected_time_to_fill_days": 32,
        "difficulty_score": 0.62,
        "hiring_risks": [
            "Immediate joiners are scarce in banking-domain Java",
            "Compensation may need to sit at band top for immediate joiners",
        ],
        "assumptions_made": [
            "Assumed on-site Chennai unless otherwise noted",
            "Assumed full-time engagement",
        ],
        "ambiguities": ["Notice period tolerance not specified"],
        "clarifying_questions": [
            "Are there sponsorship constraints?",
            "Is there flexibility on the immediate-joiner requirement?",
        ],
        "recommended_interview_panel": [
            {"role": "Tech Lead", "why": "System design + Java depth"},
            {"role": "Engineering Manager", "why": "Team + delivery fit"},
            {"role": "Domain SME (Banking)", "why": "Domain evaluation"},
            {"role": "Bar Raiser", "why": "Long-term potential"},
        ],
        "recommended_sourcing_channels": [
            {"channel": "Naukri", "priority": "P0",
             "why": "Highest-density Chennai Java talent pool"},
            {"channel": "LinkedIn", "priority": "P0",
             "why": "Best for banking-domain filtering"},
            {"channel": "Referrals", "priority": "P1",
             "why": "Referrals convert 3x faster; strong internal Java org"},
            {"channel": "Internal ATS", "priority": "P1",
             "why": "Rehiring past applicants"},
        ],
        "generated_jd": {
            "title": "Senior Java Developer — Banking Platform",
            "one_liner": "Build resilient banking micro-services on Spring Boot + Kafka.",
            "responsibilities": [
                "Own high-throughput banking micro-services on Spring Boot",
                "Design event-driven flows on Kafka",
                "Champion SRE culture, uptime, and observability",
                "Partner with product + risk teams",
            ],
            "requirements": [
                "8+ years Java, Spring Boot, Microservices",
                "Kafka experience in production",
                "Banking or fintech domain",
                "Strong system design skills",
            ],
            "nice_to_have": ["Kubernetes", "AWS", "Payment rails experience"],
            "team_context": "10-engineer platform team, US-India co-located.",
            "growth_path": "Staff Engineer track within 24 months.",
        },
        "screening_rubric": [
            {"dimension": "Technical", "weight": 0.28,
             "criteria": ["Java + Spring Boot depth", "Micro-service patterns",
                          "Kafka design"]},
            {"dimension": "Domain", "weight": 0.15,
             "criteria": ["Banking systems familiarity", "Compliance awareness"]},
            {"dimension": "Problem Solving", "weight": 0.15,
             "criteria": ["Debug scenario", "Trade-off reasoning"]},
            {"dimension": "Communication", "weight": 0.1,
             "criteria": ["Clarity", "Structure"]},
            {"dimension": "Leadership", "weight": 0.1,
             "criteria": ["Mentorship", "Cross-team collaboration"]},
            {"dimension": "Culture", "weight": 0.08,
             "criteria": ["Ownership", "Bar for engineering excellence"]},
            {"dimension": "Motivation", "weight": 0.08,
             "criteria": ["Reason for change", "Growth interest"]},
            {"dimension": "Availability", "weight": 0.06,
             "criteria": ["Notice period", "Start date"]},
        ],
        "confidence": 0.58,
        "reasoning_summary": ("Chennai Java + banking + immediate joiner is a "
                              "constrained combination — expect band-top offers."),
    }


async def run_intake(brief: str) -> dict[str, Any]:
    """Run the LLM intake. On failure, fall back to deterministic template."""
    api_key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not api_key:
        return {**_fallback_intake(brief), "source": "fallback"}
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
        chat = LlmChat(
            api_key=api_key,
            session_id=f"intake-{abs(hash(brief)) % 999999}",
            system_message=INTAKE_SYSTEM,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        resp = await chat.send_message(UserMessage(text=brief))
        text = resp if isinstance(resp, str) else getattr(resp, "content", str(resp))
        parsed = _extract_json(text)
        if not parsed:
            return {**_fallback_intake(brief), "source": "fallback_parse"}
        return {**parsed, "source": "llm"}
    except Exception:
        return {**_fallback_intake(brief), "source": "fallback_error"}


def to_recommendation(brief: str, intake: dict[str, Any]) -> Recommendation:
    return Recommendation(
        title=f"Intake: {intake.get('role_title', 'Role')} × {intake.get('headcount', 1)}",
        summary=intake.get("reasoning_summary") or intake.get("role_title", ""),
        action="human.review_intake",
        inputs={"brief": brief[:400]},
        confidence=ConfidenceScore.from_value(float(intake.get("confidence", 0.6))),
        reasoning=[
            ReasoningStep(step=1,
                          thought=f"Role: {intake.get('role_title')} ({intake.get('level')}) "
                                  f"in {intake.get('location')} — {intake.get('headcount')} seat(s).",
                          conclusion=f"Difficulty ~ {intake.get('difficulty_score', 0):.2f}"),
            ReasoningStep(step=2,
                          thought="Must-have: " + ", ".join(intake.get("must_have_skills", [])),
                          conclusion="Skill overlap will drive ranking."),
            ReasoningStep(step=3,
                          thought=f"Estimated comp {intake.get('compensation_currency', '')} "
                                  f"{intake.get('compensation_estimate_low', 0):,}"
                                  f"–{intake.get('compensation_estimate_high', 0):,}; "
                                  f"time-to-fill {intake.get('expected_time_to_fill_days', 30)}d.",
                          conclusion="Comp anchors the offer intelligence pass."),
        ],
        evidence=[
            Evidence(source="hiring_manager.brief", reference="verbatim",
                     excerpt=brief[:200]),
            Evidence(source="market.benchmarks", reference="internal",
                     excerpt=f"{intake.get('location', '')} · "
                             f"{intake.get('role_title', '')}"),
        ],
        tradeoffs=intake.get("assumptions_made", []),
        risks=intake.get("hiring_risks", []),
    )
