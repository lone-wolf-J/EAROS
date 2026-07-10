"""Sourcing Intelligence — multi-source parallel candidate discovery (simulated).

Real EAROS would hit LinkedIn/Dice/GitHub/ATS/etc. This module simulates the
parallel search deterministically so the UI can render a rich, believable
sourcing dashboard.
"""
from __future__ import annotations

import random
from typing import Any

from platform_core.integrations import INTEGRATIONS
from platform_core.world import Job, WorldState


SOURCING_CHANNELS: list[dict[str, Any]] = [
    {"channel": "LinkedIn", "integration_id": "int.linkedin",
     "base_matches": 220, "base_quality": 0.72, "resp_prob": 0.14},
    {"channel": "Naukri", "integration_id": "int.naukri",
     "base_matches": 480, "base_quality": 0.61, "resp_prob": 0.18},
    {"channel": "Dice", "integration_id": "int.dice",
     "base_matches": 95, "base_quality": 0.66, "resp_prob": 0.11},
    {"channel": "GitHub", "integration_id": "int.github",
     "base_matches": 60, "base_quality": 0.83, "resp_prob": 0.08},
    {"channel": "Internal ATS", "integration_id": "int.internal_ats",
     "base_matches": 42, "base_quality": 0.78, "resp_prob": 0.34},
    {"channel": "Referrals", "integration_id": "int.referrals",
     "base_matches": 18, "base_quality": 0.88, "resp_prob": 0.62},
    {"channel": "Talent Community", "integration_id": "int.community",
     "base_matches": 34, "base_quality": 0.74, "resp_prob": 0.29},
    {"channel": "Stack Overflow", "integration_id": "int.stackoverflow",
     "base_matches": 22, "base_quality": 0.77, "resp_prob": 0.06},
    {"channel": "Monster", "integration_id": "int.monster",
     "base_matches": 140, "base_quality": 0.54, "resp_prob": 0.09},
    {"channel": "Indeed", "integration_id": "int.indeed",
     "base_matches": 300, "base_quality": 0.51, "resp_prob": 0.07},
]


async def sourcing_sweep(world: WorldState, job_id: str) -> dict[str, Any]:
    """Simulate a parallel multi-source candidate sweep for a specific job."""
    job = await world.get_job(job_id)
    if not job:
        return {"error": "job not found"}

    r = random.Random(f"{job_id}-sweep")

    def _one_channel(channel: dict[str, Any]) -> dict[str, Any]:
        # Difficulty scarcity multiplier
        skill_signal = 0.9 if any(
            s.lower() in ("langgraph", "langchain", "salesforce cpq",
                          "dynamics 365 f&o", "databricks")
            for s in job.required_skills) else 1.0
        loc_signal = 1.15 if channel["channel"] == "Naukri" and job.country == "India" \
            else 1.0 if channel["channel"] == "LinkedIn" \
            else 0.8 if channel["channel"] == "Naukri" else 1.0
        matches = int(channel["base_matches"] * skill_signal * loc_signal
                      * r.uniform(0.75, 1.25))
        quality = round(channel["base_quality"] * r.uniform(0.9, 1.1), 3)
        dups = int(matches * r.uniform(0.05, 0.18))
        return {
            "channel": channel["channel"],
            "integration_id": channel["integration_id"],
            "matches": matches,
            "quality_score": min(1.0, quality),
            "duplicates_removed": dups,
            "unique_matches": max(0, matches - dups),
            "estimated_response_probability": round(
                channel["resp_prob"] * r.uniform(0.85, 1.15), 3),
            "latency_ms": r.randint(180, 3200),
            "confidence": round(0.55 + 0.3 * quality, 3),
            "status": "ok",
        }

    breakdown = [_one_channel(c) for c in SOURCING_CHANNELS]
    total_matches = sum(b["matches"] for b in breakdown)
    total_unique = sum(b["unique_matches"] for b in breakdown)
    total_dups = sum(b["duplicates_removed"] for b in breakdown)
    weighted_quality = round(
        sum(b["quality_score"] * b["unique_matches"] for b in breakdown)
        / max(1, total_unique), 3)

    return {
        "job_id": job_id,
        "job_title": job.title,
        "total_matches": total_matches,
        "unique_matches": total_unique,
        "duplicates_removed": total_dups,
        "weighted_quality": weighted_quality,
        "channels": breakdown,
    }
