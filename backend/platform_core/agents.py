"""Specialized AI Agent registry.

Agents are named intelligence facades that wrap capabilities + LLM reasoning.
Each agent reports health, latency, cost, and recent activity so the UI can
show a "living" system.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from foundation import utcnow_iso


class AgentSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")
    agent_id: str
    name: str
    tagline: str
    category: str  # intake | intelligence | sourcing | screening | interview | offer | ops | reflection
    icon: str  # lucide icon name
    color: str  # tailwind color key: indigo, emerald, amber, rose, cyan, violet
    purpose: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    depends_on_capabilities: list[str] = Field(default_factory=list)
    depends_on_agents: list[str] = Field(default_factory=list)
    version: str = "1.0.0"
    health: str = "healthy"  # healthy | degraded | offline
    executions_24h: int = 0
    avg_latency_ms: int = 0
    avg_cost_usd: float = 0.0
    success_rate: float = 0.98
    registered_at: str = Field(default_factory=utcnow_iso)


AGENT_CATALOG: list[AgentSpec] = [
    AgentSpec(
        agent_id="agent.intake",
        name="Hiring Intake Agent",
        tagline="Turns hiring conversations into structured requisitions.",
        category="intake",
        icon="MessageSquare", color="indigo",
        purpose="Parse hiring manager conversation, extract requirements, "
                "identify ambiguities, produce a structured brief.",
        inputs=["free-text hiring brief", "hiring manager profile", "team context"],
        outputs=["structured requirements", "ambiguities", "clarifying questions",
                 "initial JD draft"],
        depends_on_capabilities=[],
        executions_24h=47, avg_latency_ms=1800, avg_cost_usd=0.014,
    ),
    AgentSpec(
        agent_id="agent.jd_intelligence",
        name="JD Intelligence Agent",
        tagline="Composes market-aware job descriptions.",
        category="intake",
        icon="FileText", color="indigo",
        purpose="Generate role-appropriate JD grounded in world state + market benchmarks.",
        inputs=["structured requirements", "market benchmarks", "internal parity"],
        outputs=["job description", "screening rubric", "must-haves", "nice-to-haves"],
        depends_on_agents=["agent.intake", "agent.market_intelligence"],
        executions_24h=39, avg_latency_ms=2200, avg_cost_usd=0.021,
    ),
    AgentSpec(
        agent_id="agent.market_intelligence",
        name="Market Intelligence Agent",
        tagline="Benchmarks compensation, scarcity, and hiring difficulty.",
        category="intelligence",
        icon="LineChart", color="violet",
        purpose="Estimate compensation band, difficulty, and time-to-fill from "
                "world state + external signals.",
        inputs=["role", "location", "level"],
        outputs=["comp band", "difficulty score", "time-to-fill estimate",
                 "supply/demand ratio"],
        executions_24h=118, avg_latency_ms=420, avg_cost_usd=0.006,
    ),
    AgentSpec(
        agent_id="agent.sourcing",
        name="Sourcing Agent",
        tagline="Searches every connected talent system in parallel.",
        category="sourcing",
        icon="Radar", color="cyan",
        purpose="Query LinkedIn, Dice, GitHub, internal ATS, referrals, "
                "community, and job boards in parallel; deduplicate; rank.",
        inputs=["job requirements", "sourcing budget", "channel priorities"],
        outputs=["ranked candidate list", "channel efficacy", "dedup stats"],
        depends_on_capabilities=["cap.source_candidates"],
        executions_24h=64, avg_latency_ms=3400, avg_cost_usd=0.031,
    ),
    AgentSpec(
        agent_id="agent.resume_intelligence",
        name="Resume Intelligence Agent",
        tagline="Parses, scores, and rewrites resumes.",
        category="sourcing",
        icon="ScrollText", color="cyan",
        purpose="Extract skills, timeline, strengths/gaps; produce client-ready "
                "one-pager; redact PII when required.",
        inputs=["resume file", "job requirements"],
        outputs=["parsed profile", "fit analysis", "client version", "redacted version"],
        depends_on_capabilities=["cap.screen_candidate"],
        executions_24h=203, avg_latency_ms=1900, avg_cost_usd=0.011,
    ),
    AgentSpec(
        agent_id="agent.ranking",
        name="Candidate Ranking Agent",
        tagline="Composite scoring across skills, experience, salary, risk.",
        category="sourcing",
        icon="Trophy", color="cyan",
        purpose="Rank candidates on a multi-objective scorecard.",
        inputs=["candidates", "job requirements"],
        outputs=["ranked list", "score breakdown", "recommendation per candidate"],
        depends_on_capabilities=["cap.screen_candidate"],
        executions_24h=88, avg_latency_ms=650, avg_cost_usd=0.004,
    ),
    AgentSpec(
        agent_id="agent.outreach",
        name="Outreach Agent",
        tagline="Personalized multi-channel outreach with A/B variants.",
        category="sourcing",
        icon="Send", color="emerald",
        purpose="Draft email, LinkedIn, SMS, WhatsApp, and voice scripts with "
                "response-probability estimates.",
        inputs=["candidate profile", "job", "channel", "tone"],
        outputs=["draft messages", "A/B variants", "response probability",
                 "follow-up sequence"],
        depends_on_capabilities=["cap.draft_outreach"],
        executions_24h=311, avg_latency_ms=1600, avg_cost_usd=0.009,
    ),
    AgentSpec(
        agent_id="agent.response_monitor",
        name="Response Monitor",
        tagline="Watches inboxes, LinkedIn, and SMS for candidate replies.",
        category="sourcing",
        icon="Radio", color="emerald",
        purpose="Track candidate responses across channels; trigger next action.",
        inputs=["outreach batch"],
        outputs=["reply signals", "sentiment", "next-step suggestion"],
        executions_24h=502, avg_latency_ms=280, avg_cost_usd=0.002,
    ),
    AgentSpec(
        agent_id="agent.screening",
        name="Screening Agent",
        tagline="8-dimension rubric-based screening.",
        category="screening",
        icon="ClipboardCheck", color="amber",
        purpose="Score candidates on communication, technical, leadership, "
                "culture, problem-solving, domain, motivation, availability.",
        inputs=["candidate profile", "transcript or notes", "rubric"],
        outputs=["8-dim rubric scores", "recommendation", "risks"],
        depends_on_capabilities=["cap.screen_candidate"],
        executions_24h=76, avg_latency_ms=2700, avg_cost_usd=0.024,
    ),
    AgentSpec(
        agent_id="agent.interview_intelligence",
        name="Interview Intelligence Agent",
        tagline="Real-time interview co-pilot for humans.",
        category="interview",
        icon="Mic", color="amber",
        purpose="Live transcription, sentiment, STAR extraction, and follow-up "
                "question suggestions during interviews.",
        inputs=["audio stream", "interview plan"],
        outputs=["transcript", "sentiment timeline", "STAR items", "follow-up prompts"],
        depends_on_capabilities=["cap.schedule_interview"],
        executions_24h=22, avg_latency_ms=95, avg_cost_usd=0.052,
    ),
    AgentSpec(
        agent_id="agent.offer_intelligence",
        name="Offer Intelligence Agent",
        tagline="Compensation modeling with parity + acceptance forecast.",
        category="offer",
        icon="BadgeDollarSign", color="emerald",
        purpose="Recommend offer package; estimate acceptance probability; "
                "flag internal parity risk.",
        inputs=["candidate", "job band", "internal parity data"],
        outputs=["offer package", "acceptance probability", "parity delta"],
        depends_on_capabilities=["cap.generate_offer"],
        executions_24h=18, avg_latency_ms=1300, avg_cost_usd=0.017,
    ),
    AgentSpec(
        agent_id="agent.reference_check",
        name="Reference Check Agent",
        tagline="Structured reference outreach and summary.",
        category="offer",
        icon="ShieldCheck", color="emerald",
        purpose="Outreach references, capture structured feedback, summarize.",
        inputs=["candidate references"],
        outputs=["reference summaries", "risk flags"],
        executions_24h=9, avg_latency_ms=1500, avg_cost_usd=0.012,
    ),
    AgentSpec(
        agent_id="agent.background_verification",
        name="Background Verification Agent",
        tagline="Coordinates BGV vendors and consolidates results.",
        category="offer",
        icon="ScanSearch", color="emerald",
        purpose="Coordinate education/employment/criminal checks; monitor SLA.",
        inputs=["candidate", "vendor"],
        outputs=["verification status", "flags"],
        executions_24h=12, avg_latency_ms=6200, avg_cost_usd=0.008,
    ),
    AgentSpec(
        agent_id="agent.planner",
        name="Planner",
        tagline="Task decomposition + capability selection.",
        category="ops",
        icon="GitBranch", color="indigo",
        purpose="Produce an executable, policy-safe plan grounded in world state.",
        inputs=["goal", "world state facts"],
        outputs=["plan", "reasoning", "confidence"],
        executions_24h=142, avg_latency_ms=3900, avg_cost_usd=0.028,
    ),
    AgentSpec(
        agent_id="agent.runtime",
        name="Execution Runtime",
        tagline="Deterministic orchestrator with retries + policy gate.",
        category="ops",
        icon="Cpu", color="indigo",
        purpose="Execute plans step-by-step; enforce policy; emit events.",
        inputs=["plan", "user context"],
        outputs=["step results", "events"],
        executions_24h=142, avg_latency_ms=1200, avg_cost_usd=0.003,
    ),
    AgentSpec(
        agent_id="agent.policy",
        name="Policy Engine",
        tagline="First-class policy evaluator on every action.",
        category="ops",
        icon="ShieldAlert", color="rose",
        purpose="Evaluate every capability invocation against active policies.",
        inputs=["policy context"],
        outputs=["decision", "policies referenced"],
        executions_24h=418, avg_latency_ms=80, avg_cost_usd=0.001,
    ),
    AgentSpec(
        agent_id="agent.reflection",
        name="Reflection Agent",
        tagline="Post-execution learning; improves future plans.",
        category="reflection",
        icon="Sparkles", color="violet",
        purpose="Compare predictions to outcomes; propose planner tuning + "
                "policy suggestions.",
        inputs=["execution record", "outcome"],
        outputs=["lessons", "planner adjustments", "policy suggestions"],
        executions_24h=142, avg_latency_ms=980, avg_cost_usd=0.007,
    ),
]


def list_agents() -> list[AgentSpec]:
    return AGENT_CATALOG


def get_agent(agent_id: str) -> AgentSpec | None:
    return next((a for a in AGENT_CATALOG if a.agent_id == agent_id), None)
