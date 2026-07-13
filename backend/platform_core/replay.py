"""Execution replay — reconstruct a full lifecycle from immutable events for
the Deep-Dive page.

Returns swimlane messages (Planner → Runtime → Policy → Capability →
World/Reflection) with timing, payloads, and human-readable descriptions.
"""
from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase


LANE_MAP = {
    "runtime.plan.created":              ("planner",    "Planner produced a plan"),
    "runtime.execution.started":         ("runtime",    "Runtime started execution"),
    "runtime.execution.completed":       ("runtime",    "Runtime completed execution"),
    "runtime.execution.failed":          ("runtime",    "Runtime execution failed"),
    "runtime.step.started":              ("runtime",    "Runtime dispatched step"),
    "runtime.step.completed":            ("capability", "Capability finished step"),
    "policy.evaluated":                  ("policy",     "Policy Engine evaluated"),
    "policy.violated":                   ("policy",     "Policy Engine denied"),
    "governance.approval.requested":     ("governance", "Approval requested"),
    "governance.approval.granted":       ("governance", "Approval granted"),
    "governance.approval.denied":        ("governance", "Approval denied"),
    "world.candidate.stage_changed":     ("world",      "World State mutated"),
    "world.offer.extended":              ("world",      "Offer written to World State"),
    "reflection.created":                ("reflection", "Reflection recorded"),
}

LANES = ["planner", "policy", "runtime", "capability", "world", "governance", "reflection"]


def _humanize_payload(event_type: str, payload: dict[str, Any]) -> str:
    """Turn the event payload into a plain-English one-liner."""
    if event_type == "policy.evaluated":
        return (f"Decision: {payload.get('decision', '—').upper()} · "
                f"{payload.get('reason', '')}")
    if event_type == "policy.violated":
        return f"Denied: {payload.get('reason', 'policy violation')}"
    if event_type == "runtime.step.started":
        cap = payload.get("capability_id", "?")
        return f"Dispatching {cap}"
    if event_type == "runtime.step.completed":
        cap = payload.get("capability_id", "?")
        ok = payload.get("ok")
        facts = payload.get("facts") or []
        head = f"{cap} " + ("succeeded" if ok else "failed")
        if facts:
            head += " · " + " · ".join(facts[:2])
        return head
    if event_type == "runtime.execution.started":
        return f"Goal: {payload.get('goal', '')[:80]}"
    if event_type == "runtime.execution.completed":
        return f"All {payload.get('steps', 0)} step(s) completed"
    if event_type == "runtime.execution.failed":
        return f"Reason: {payload.get('reason', '')}"
    if event_type == "governance.approval.requested":
        return f"Held for approval: {payload.get('reason', '')}"
    if event_type == "governance.approval.granted":
        return f"Approved{': ' + payload.get('note') if payload.get('note') else ''}"
    if event_type == "governance.approval.denied":
        return f"Denied{': ' + payload.get('note') if payload.get('note') else ''}"
    if event_type == "reflection.created":
        improvements = payload.get("improvements") or []
        return "Lesson: " + (improvements[0] if improvements else "recorded")
    if event_type == "runtime.plan.created":
        return f"Stage: {payload.get('stage', 'plan')}"
    return ""


async def list_replayable_executions(
    db: AsyncIOMotorDatabase, organization_id: str, limit: int = 30
) -> list[dict[str, Any]]:
    """Return execution runs available for replay, plus scenario correlation ids."""
    # Executions from the runtime
    ex_docs = await db.executions.find(
        {"organization_id": organization_id}, {"_id": 0}
    ).sort("started_at", -1).to_list(limit)
    items = []
    seen = set()
    for e in ex_docs:
        cid = e.get("correlation_id")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        items.append({
            "correlation_id": cid,
            "goal": e.get("goal"),
            "status": e.get("status"),
            "started_at": e.get("started_at"),
            "steps": len(e.get("steps") or []),
            "kind": "execution",
        })

    # Scenario runs (correlation_id may not have an executions doc if scenario
    # ran multiple executions under the same correlation).
    scenario_events = await db.events.find(
        {"organization_id": organization_id,
         "event_type": "runtime.plan.created",
         "actor": "agent.intake"}, {"_id": 0}
    ).sort("occurred_at", -1).to_list(limit)
    for e in scenario_events:
        cid = e.get("correlation_id")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        items.append({
            "correlation_id": cid,
            "goal": f"Scenario · {e.get('subject_id', '')}",
            "status": "scenario",
            "started_at": e.get("occurred_at"),
            "steps": 0,
            "kind": "scenario",
        })
    return items


async def replay_execution(
    db: AsyncIOMotorDatabase, correlation_id: str
) -> dict[str, Any]:
    """Return the ordered event trace + swimlane messages for the correlation id."""
    events = await db.events.find(
        {"correlation_id": correlation_id}, {"_id": 0}
    ).sort("occurred_at", 1).to_list(1000)

    messages: list[dict[str, Any]] = []
    for e in events:
        lane, label = LANE_MAP.get(e["event_type"], ("runtime", e["event_type"]))
        payload = e.get("payload") or {}
        # Extract common fields
        cap_id = payload.get("capability_id")
        confidence = payload.get("confidence")
        # Policies referenced
        policies = payload.get("policies") or []
        message = {
            "event_id": e["event_id"],
            "occurred_at": e["occurred_at"],
            "lane": lane,
            "event_type": e["event_type"],
            "actor": e.get("actor"),
            "subject_type": e.get("subject_type"),
            "subject_id": e.get("subject_id"),
            "label": label,
            "human": _humanize_payload(e["event_type"], payload),
            "capability_id": cap_id,
            "confidence": confidence,
            "policies": policies,
            "payload": payload,
        }
        messages.append(message)

    # Approvals related to this correlation
    approval_ids = []
    for m in messages:
        if "approval_id" in (m["payload"] or {}):
            approval_ids.append(m["payload"]["approval_id"])
    approvals: list[dict[str, Any]] = []
    if approval_ids:
        approvals = await db.approvals.find(
            {"approval_id": {"$in": approval_ids}}, {"_id": 0}
        ).to_list(50)

    # Execution records under this correlation
    exec_docs = await db.executions.find(
        {"correlation_id": correlation_id}, {"_id": 0}
    ).sort("started_at", 1).to_list(50)

    # Timing + rollup
    started = messages[0]["occurred_at"] if messages else None
    ended = messages[-1]["occurred_at"] if messages else None
    from datetime import datetime
    duration_ms = 0
    if started and ended:
        try:
            duration_ms = int((datetime.fromisoformat(ended) -
                                datetime.fromisoformat(started)).total_seconds() * 1000)
        except Exception:
            pass

    steps_total = sum(1 for m in messages if m["event_type"] == "runtime.step.completed")
    auto_approved = steps_total  # if execution completed with steps, they were policy-allowed
    human_gated = sum(1 for m in messages if m["event_type"] == "governance.approval.requested")

    # Per-agent cost tally (deterministic mapping from event_type -> agent avg cost)
    from platform_core.agents import AGENT_CATALOG
    agent_cost = {a.agent_id: a.avg_cost_usd for a in AGENT_CATALOG}
    total_cost = 0.0
    for m in messages:
        if m["event_type"] == "runtime.plan.created":
            total_cost += agent_cost.get("agent.planner", 0)
        elif m["event_type"] == "runtime.step.completed":
            total_cost += agent_cost.get("agent.runtime", 0)
        elif m["event_type"].startswith("policy."):
            total_cost += agent_cost.get("agent.policy", 0)
        elif m["event_type"] == "reflection.created":
            total_cost += agent_cost.get("agent.reflection", 0)

    return {
        "correlation_id": correlation_id,
        "lanes": LANES,
        "messages": messages,
        "approvals": approvals,
        "executions": exec_docs,
        "duration_ms": duration_ms,
        "started_at": started,
        "ended_at": ended,
        "steps_total": steps_total,
        "auto_approved": auto_approved,
        "human_gated": human_gated,
        "total_cost_usd": round(total_cost, 4),
    }
