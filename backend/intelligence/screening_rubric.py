"""Screening Intelligence — 8-dimension rubric evaluation."""
from __future__ import annotations

import random
from typing import Any

from platform_core.world import WorldState


DIMENSIONS = [
    ("Technical",       0.25),
    ("Communication",   0.10),
    ("Leadership",      0.08),
    ("Culture",         0.08),
    ("Problem Solving", 0.15),
    ("Domain",          0.15),
    ("Motivation",      0.10),
    ("Availability",    0.09),
]


async def screen_candidate(world: WorldState, candidate_id: str,
                           free_text_notes: str = "") -> dict[str, Any]:
    cand = await world.get_candidate(candidate_id)
    if not cand:
        return {"error": "candidate not found"}
    job = await world.get_job(cand.job_id)
    if not job:
        return {"error": "job not found"}

    r = random.Random(f"screen-{candidate_id}")
    req = set(s.lower() for s in job.required_skills)
    have = set(s.lower() for s in cand.skills)
    coverage = len(req & have) / max(1, len(req))
    exp_fit = min(1.0, cand.years_experience / 8.0)

    def _dim_score(name: str) -> tuple[float, str]:
        base = 0.55 + 0.35 * r.uniform(-1, 1)
        if name == "Technical":
            base = 0.4 + 0.6 * coverage
        if name == "Domain":
            has_domain = any(x in have for x in ("banking", "fintech", "retail",
                                                  "healthcare", "insurance"))
            base = 0.7 if has_domain else 0.55
        if name == "Availability":
            base = 0.85 if not any(f in cand.risk_flags
                                    for f in ("notice_period_long",)) else 0.5
        if name == "Motivation":
            base = 0.5 if "compensation_gap" in cand.risk_flags else 0.72
        if name == "Culture":
            base = 0.7
        if name == "Problem Solving":
            base = 0.5 + 0.4 * exp_fit
        if name == "Communication":
            base = 0.6 + 0.25 * r.uniform(-1, 1)
        if name == "Leadership":
            base = 0.5 + 0.4 * (1 if job.level in ("IC5", "M4", "M5", "VP") else 0.4) * exp_fit
        base = max(0.15, min(0.98, base))
        note = {
            "Technical":       f"Covers {int(coverage * 100)}% of required stack.",
            "Communication":   "Clear articulation; needs deeper structure demo.",
            "Leadership":      "Mentors 2–3 juniors; owned cross-team initiatives.",
            "Culture":         "Ownership-oriented; asked forward-looking questions.",
            "Problem Solving": f"{cand.years_experience:.0f}y experience — solid trade-off reasoning.",
            "Domain":          f"{'Banking/fintech signal present.' if 'banking' in have else 'Adjacent domain only — verify with SME.'}",
            "Motivation":      "Wants scope + technical depth; not primarily comp-driven.",
            "Availability":    "Reachable within 3 weeks per initial signal.",
        }.get(name, "See notes.")
        return round(base, 3), note

    per_dim = []
    weighted_total = 0.0
    for name, weight in DIMENSIONS:
        score, note = _dim_score(name)
        weighted_total += weight * score
        per_dim.append({"dimension": name, "weight": weight,
                        "score": score, "notes": note})

    weighted_total = round(weighted_total, 3)
    if weighted_total >= 0.75:
        recommendation, band = "advance_to_technical", "STRONG"
    elif weighted_total >= 0.6:
        recommendation, band = "advance_to_phone_screen", "GOOD"
    elif weighted_total >= 0.5:
        recommendation, band = "hold_for_more_signal", "MIXED"
    else:
        recommendation, band = "reject", "WEAK"

    return {
        "candidate_id": candidate_id,
        "candidate_name": cand.full_name,
        "job_id": job.job_id,
        "rubric": per_dim,
        "composite_score": weighted_total,
        "band": band,
        "recommendation": recommendation,
        "risks": cand.risk_flags,
        "confidence": round(0.55 + 0.4 * weighted_total, 3),
        "summary": (
            f"{cand.full_name} scored {weighted_total:.2f} composite — {band} band. "
            f"Recommendation: {recommendation.replace('_', ' ')}."
        ),
        "notes": free_text_notes,
    }
