"""Governance — audit, event stream, approvals, replay.

Immutable event log. Approvals workflow. Policy violation ledger.
"""
from __future__ import annotations

from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, ConfigDict, Field

from foundation import (
    DomainEvent,
    EventType,
    new_approval_id,
    utcnow_iso,
)


class Approval(BaseModel):
    model_config = ConfigDict(extra="ignore")
    approval_id: str = Field(default_factory=new_approval_id)
    organization_id: str
    subject_type: str  # "offer", "shortlist", "hiring_strategy", "capability_execution"
    subject_id: str
    requested_by: str
    reason: str
    context: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"  # pending | granted | denied
    decided_by: Optional[str] = None
    decided_at: Optional[str] = None
    decision_note: Optional[str] = None
    created_at: str = Field(default_factory=utcnow_iso)


class Governance:
    """Governance service — writes immutable events, manages approvals."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def emit(self, event: DomainEvent) -> DomainEvent:
        """Append immutable event to the audit stream."""
        await self.db.events.insert_one(event.model_dump())
        return event

    async def list_events(
        self,
        organization_id: Optional[str] = None,
        event_type: Optional[str] = None,
        subject_id: Optional[str] = None,
        limit: int = 200,
    ) -> list[DomainEvent]:
        q: dict[str, Any] = {}
        if organization_id:
            q["organization_id"] = organization_id
        if event_type:
            q["event_type"] = event_type
        if subject_id:
            q["subject_id"] = subject_id
        docs = await self.db.events.find(q, {"_id": 0}).sort("occurred_at", -1).to_list(limit)
        return [DomainEvent(**d) for d in docs]

    async def replay(self, correlation_id: str) -> list[DomainEvent]:
        docs = await self.db.events.find(
            {"correlation_id": correlation_id}, {"_id": 0}
        ).sort("occurred_at", 1).to_list(1000)
        return [DomainEvent(**d) for d in docs]

    # approvals
    async def request_approval(self, a: Approval) -> Approval:
        await self.db.approvals.insert_one(a.model_dump())
        corr = (a.context or {}).get("correlation_id")
        await self.emit(DomainEvent(
            event_type=EventType.APPROVAL_REQUESTED,
            actor=a.requested_by,
            subject_type=a.subject_type,
            subject_id=a.subject_id,
            organization_id=a.organization_id,
            payload={"approval_id": a.approval_id, "reason": a.reason},
            correlation_id=corr,
        ))
        return a

    async def list_approvals(self, organization_id: str, status: Optional[str] = None) -> list[Approval]:
        q: dict[str, Any] = {"organization_id": organization_id}
        if status:
            q["status"] = status
        docs = await self.db.approvals.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
        return [Approval(**d) for d in docs]

    async def get_approval(self, approval_id: str) -> Optional[Approval]:
        doc = await self.db.approvals.find_one({"approval_id": approval_id}, {"_id": 0})
        return Approval(**doc) if doc else None

    async def decide_approval(
        self, approval_id: str, decision: str, decided_by: str, note: Optional[str] = None
    ) -> Optional[Approval]:
        await self.db.approvals.update_one(
            {"approval_id": approval_id},
            {"$set": {
                "status": decision,
                "decided_by": decided_by,
                "decided_at": utcnow_iso(),
                "decision_note": note,
            }},
        )
        approval = await self.get_approval(approval_id)
        if approval:
            corr = (approval.context or {}).get("correlation_id")
            await self.emit(DomainEvent(
                event_type=(
                    EventType.APPROVAL_GRANTED if decision == "granted"
                    else EventType.APPROVAL_DENIED
                ),
                actor=decided_by,
                subject_type=approval.subject_type,
                subject_id=approval.subject_id,
                organization_id=approval.organization_id,
                payload={"approval_id": approval_id, "note": note},
                correlation_id=corr,
            ))
        return approval
