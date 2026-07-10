"""Voice Interview Intelligence — mock live interview.

Runs a scripted turn-based interview: given candidate profile + question index,
returns the next question, ambient transcript, sentiment, and a running
evaluation. Real EAROS would connect to Realtime STT/TTS.
"""
from __future__ import annotations

import random
from typing import Any

from platform_core.world import WorldState


TECHNICAL_BANK = [
    "Walk me through the last production incident you owned end-to-end.",
    "How would you design a Kafka topic layout for a high-throughput banking ledger?",
    "Describe a trade-off you made between latency and consistency.",
    "How do you decide whether to introduce a new micro-service vs extend an existing one?",
    "Tell me about a system you scaled 10x — where did the bottlenecks appear?",
]
BEHAVIORAL_BANK = [
    "Tell me about a time you disagreed with a leader and how you resolved it.",
    "Walk me through a project you inherited that was underperforming.",
    "How do you handle mentoring engineers less senior than you?",
    "Describe a failure that shaped how you approach engineering.",
]
DOMAIN_BANK = [
    "How does regulatory constraint shape your API design in banking?",
    "How do you approach data residency across India and USA?",
]


async def start_interview(world: WorldState, candidate_id: str) -> dict[str, Any]:
    cand = await world.get_candidate(candidate_id)
    if not cand:
        return {"error": "candidate not found"}
    r = random.Random(f"interview-{candidate_id}")
    plan = (
        [{"kind": "opener", "text": f"Hi {cand.full_name.split()[0]}, welcome. "
                                     "Let's start with a quick intro."}]
        + [{"kind": "technical", "text": q} for q in r.sample(TECHNICAL_BANK, 3)]
        + [{"kind": "behavioral", "text": q} for q in r.sample(BEHAVIORAL_BANK, 2)]
        + [{"kind": "domain", "text": r.choice(DOMAIN_BANK)}]
        + [{"kind": "closing", "text": "What questions do you have for us?"}]
    )
    return {
        "candidate_id": candidate_id,
        "candidate_name": cand.full_name,
        "plan": plan,
        "duration_target_min": 45,
        "interviewer_agent": "agent.interview_intelligence",
    }


def _mock_answer(question: str, seed: str) -> str:
    r = random.Random(f"answer-{seed}-{question}")
    templates = [
        "So the way I approached that was to first quantify the blast radius. "
        "We had roughly {n}k RPS and a p99 of {p}ms which meant… (candidate expands)",
        "Great question — the trade-off I made there was around consistency. "
        "We chose eventual consistency because the business could tolerate a "
        "{n}-second window, and it unlocked a {p}x throughput improvement.",
        "The framework I use is: identify who owns the outcome, then find the "
        "smallest reversible experiment. In this case, we ran a {n}-day shadow "
        "before flipping traffic.",
    ]
    return r.choice(templates).format(n=r.randint(3, 40), p=r.randint(20, 300))


async def turn(world: WorldState, candidate_id: str, question_index: int,
               transcript_so_far: str = "") -> dict[str, Any]:
    plan_data = await start_interview(world, candidate_id)
    if "error" in plan_data:
        return plan_data
    plan = plan_data["plan"]
    if question_index >= len(plan):
        return {"done": True, "summary_ready": True,
                "candidate_id": candidate_id}
    step = plan[question_index]
    r = random.Random(f"turn-{candidate_id}-{question_index}")
    answer = _mock_answer(step["text"], candidate_id)
    sentiment = round(r.uniform(0.55, 0.9), 2)
    signal_strength = round(0.5 + 0.4 * r.uniform(0, 1), 2)
    star_extracted = None
    if step["kind"] in ("behavioral", "domain"):
        star_extracted = {
            "situation": "Owned a payment ledger migration under a 30-day deadline.",
            "task": "Design and implement an event-sourced replacement.",
            "action": "Introduced Kafka with idempotent consumers; ran shadow "
                      "traffic for 12 days.",
            "result": "Zero data loss; p99 improved from 260ms to 78ms.",
        }
    followup = None
    if step["kind"] == "technical":
        followup = "Great — can you walk me through how you'd handle back-pressure?"
    elif step["kind"] == "behavioral":
        followup = "What would you do differently the second time?"

    return {
        "question_index": question_index,
        "total_questions": len(plan),
        "question": step,
        "mock_candidate_answer": answer,
        "sentiment": sentiment,
        "signal_strength": signal_strength,
        "star_extracted": star_extracted,
        "suggested_followup": followup,
        "running_evaluation": {
            "communication": round(r.uniform(0.6, 0.9), 2),
            "technical_depth": round(r.uniform(0.55, 0.9), 2),
            "problem_solving": round(r.uniform(0.55, 0.9), 2),
            "domain": round(r.uniform(0.5, 0.85), 2),
        },
    }


async def summarize_interview(world: WorldState, candidate_id: str,
                              turns: list[dict[str, Any]]) -> dict[str, Any]:
    cand = await world.get_candidate(candidate_id)
    if not cand:
        return {"error": "candidate not found"}
    r = random.Random(f"sum-{candidate_id}")
    avg_signal = sum(t.get("signal_strength", 0) for t in turns) / max(1, len(turns))
    avg_sentiment = sum(t.get("sentiment", 0) for t in turns) / max(1, len(turns))
    strengths = [
        "Structured, first-principles reasoning",
        "Comfortable with distributed-systems trade-offs",
        "Strong on incident-response storytelling",
    ]
    concerns = []
    if avg_signal < 0.65:
        concerns.append("Signal thin on the domain block — schedule SME follow-up.")
    if avg_sentiment < 0.65:
        concerns.append("Sentiment dipped mid-interview — verify motivation.")
    recommendation = (
        "advance" if avg_signal >= 0.7 else
        "second_round" if avg_signal >= 0.6 else
        "hold_or_reject"
    )
    return {
        "candidate_id": candidate_id,
        "candidate_name": cand.full_name,
        "duration_min": 42,
        "avg_signal": round(avg_signal, 3),
        "avg_sentiment": round(avg_sentiment, 3),
        "strengths": strengths,
        "concerns": concerns,
        "recommendation": recommendation,
        "confidence": round(0.55 + 0.35 * avg_signal, 3),
        "summary_narrative": (
            f"{cand.full_name} demonstrated {round(avg_signal * 100)}% average signal "
            f"strength across technical, behavioral, and domain blocks. "
            f"Sentiment stayed at {round(avg_sentiment * 100)}%. Recommendation: "
            f"{recommendation.replace('_', ' ')}."
        ),
    }
