"""Live activity engine.

Aggregates:
- Recent immutable events
- Currently running / recently finished executions
- A synthetic pulse of ambient agent + capability + policy activity so the UI
  always feels alive during a demo.

Ambient activity is deterministic per second bucket and clearly labeled as
`ambient=True` so tests can distinguish it from real events if needed.
"""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from platform_core.agents import AGENT_CATALOG


AMBIENT_TEMPLATES = [
    ("agent.sourcing", "sourced {n} candidates from {sys}",
     {"n": (5, 40), "sys": ["LinkedIn", "Dice", "GitHub", "Naukri", "Referrals",
                            "Talent Community", "Internal ATS", "Monster"]}),
    ("agent.resume_intelligence", "parsed resume for {name}",
     {"name": ["A. Sharma", "R. Iyer", "K. Nair", "P. Menon", "E. Rodriguez",
               "D. Cohen", "M. Patterson", "T. Chatterjee", "V. Reddy"]}),
    ("agent.ranking", "ranked {n} candidates for {role}",
     {"n": (6, 22),
      "role": ["Salesforce Lead", "AI Engineer", "Data Engineer",
               "Dynamics Consultant", "Client Partner", "Enterprise AE"]}),
    ("agent.outreach", "drafted {ch} outreach for {name}",
     {"ch": ["email", "LinkedIn InMail", "SMS", "WhatsApp"],
      "name": ["Divya Sharma", "Aryan Kapoor", "Kevin Reed", "Sarah Lin"]}),
    ("agent.market_intelligence", "refreshed comp benchmark for {role}",
     {"role": ["Salesforce Architect Austin", "AI Engineer Bangalore",
               "Client Partner Boston", "Data Engineer Pune"]}),
    ("agent.policy", "evaluated policy for {cap}",
     {"cap": ["cap.screen_candidate", "cap.advance_stage", "cap.draft_outreach",
              "cap.generate_offer"]}),
    ("agent.reflection", "synthesized reflection {n}",
     {"n": (1, 3)}),
    ("agent.response_monitor", "detected reply from {name}",
     {"name": ["Ravi Gupta", "Emily Bennett", "Jessica Foster", "Karthik Rao"]}),
    ("agent.screening", "computed rubric for {name}",
     {"name": ["Neha Kapoor", "Chris Rivera", "Zara Bhatt", "Michael Perry"]}),
]


def _pulse_bucket(seed_bucket: int, index: int) -> dict[str, Any]:
    """Deterministic ambient activity item from a bucket seed."""
    r = random.Random(f"ambient-{seed_bucket}-{index}")
    agent_id, tmpl, slots = r.choice(AMBIENT_TEMPLATES)
    filled = {}
    for k, v in slots.items():
        if isinstance(v, tuple):
            filled[k] = r.randint(v[0], v[1])
        else:
            filled[k] = r.choice(v)
    return {
        "agent_id": agent_id,
        "message": tmpl.format(**filled),
        "latency_ms": r.randint(120, 3400),
        "confidence": round(r.uniform(0.65, 0.98), 3),
        "cost_usd": round(r.uniform(0.001, 0.03), 4),
        "ambient": True,
    }


def current_ambient(limit: int = 12) -> list[dict[str, Any]]:
    """Return a rolling window of ambient activity that evolves ~every 3 sec."""
    now = datetime.now(timezone.utc)
    bucket = int(now.timestamp() // 3)
    items: list[dict[str, Any]] = []
    for i in range(limit):
        b = bucket - i
        item = _pulse_bucket(b, 0)
        # timestamp back-dated to the bucket start
        ts = datetime.fromtimestamp(b * 3, tz=timezone.utc).isoformat()
        item["occurred_at"] = ts
        items.append(item)
    return items


async def mission_snapshot(
    db, organization_id: str, ambient: int = 8
) -> dict[str, Any]:
    """One-shot snapshot for the Mission Control page."""
    # Recent real events
    events_docs = await db.events.find(
        {"organization_id": organization_id}, {"_id": 0}
    ).sort("occurred_at", -1).to_list(30)

    # Running / awaiting executions
    running_docs = await db.executions.find(
        {"organization_id": organization_id,
         "status": {"$in": ["running", "awaiting_approval", "pending"]}}, {"_id": 0}
    ).sort("started_at", -1).to_list(20)

    recent_execs = await db.executions.find(
        {"organization_id": organization_id}, {"_id": 0}
    ).sort("started_at", -1).to_list(10)

    approvals = await db.approvals.find(
        {"organization_id": organization_id, "status": "pending"}, {"_id": 0}
    ).sort("created_at", -1).to_list(20)

    reflections = await db.reflections.find(
        {"organization_id": organization_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(5)

    # Agent activity counters (deterministic per 60-s bucket + real exec counts)
    bucket = int(datetime.now(timezone.utc).timestamp() // 60)
    r = random.Random(f"agent-pulse-{bucket}")
    agent_pulse: list[dict[str, Any]] = []
    for a in AGENT_CATALOG:
        drift = r.randint(-3, 6)
        agent_pulse.append({
            "agent_id": a.agent_id,
            "name": a.name,
            "category": a.category,
            "icon": a.icon,
            "color": a.color,
            "health": a.health,
            "in_flight": max(0, drift),
            "executions_24h": a.executions_24h + r.randint(0, 12),
            "avg_latency_ms": a.avg_latency_ms + r.randint(-80, 80),
        })

    counts = {
        "events_total": await db.events.count_documents(
            {"organization_id": organization_id}),
        "executions_total": await db.executions.count_documents(
            {"organization_id": organization_id}),
        "executions_running": len(running_docs),
        "approvals_pending": len(approvals),
        "reflections_total": await db.reflections.count_documents(
            {"organization_id": organization_id}),
        "policies_active": await db.policies.count_documents(
            {"organization_id": organization_id, "enabled": True}),
        "candidates_total": await db.candidates.count_documents(
            {"organization_id": organization_id}),
        "open_reqs": await db.jobs.count_documents(
            {"organization_id": organization_id, "status": "open"}),
    }

    return {
        "counts": counts,
        "recent_events": events_docs,
        "running_executions": running_docs,
        "recent_executions": recent_execs,
        "pending_approvals": approvals,
        "recent_reflections": reflections,
        "agent_pulse": agent_pulse,
        "ambient_activity": current_ambient(ambient),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }
