"""Reflection — post-execution learning.

Cannot rewrite history. Proposes future improvements based on prediction vs. outcome.
"""
from __future__ import annotations

from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, ConfigDict, Field

from foundation import (
    DomainEvent,
    EventType,
    new_reflection_id,
    utcnow_iso,
)
from platform_core.governance import Governance


class ReflectionReport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    reflection_id: str = Field(default_factory=new_reflection_id)
    organization_id: str
    execution_id: Optional[str] = None
    subject_type: str
    subject_id: str
    what_happened: str
    why: str
    what_succeeded: list[str] = Field(default_factory=list)
    what_failed: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utcnow_iso)


class Reflection:
    def __init__(self, db: AsyncIOMotorDatabase, governance: Governance):
        self.db = db
        self.governance = governance

    async def record(self, r: ReflectionReport) -> ReflectionReport:
        await self.db.reflections.insert_one(r.model_dump())
        await self.governance.emit(DomainEvent(
            event_type=EventType.REFLECTION_CREATED,
            actor="reflection",
            subject_type=r.subject_type,
            subject_id=r.subject_id,
            organization_id=r.organization_id,
            payload={"reflection_id": r.reflection_id, "improvements": r.improvements},
            correlation_id=r.execution_id,
        ))
        return r

    async def list_reports(self, organization_id: str, limit: int = 50) -> list[ReflectionReport]:
        docs = await self.db.reflections.find(
            {"organization_id": organization_id}, {"_id": 0}
        ).sort("created_at", -1).to_list(limit)
        return [ReflectionReport(**d) for d in docs]

    async def summarize_execution(self, execution_doc: dict[str, Any]) -> ReflectionReport:
        """Auto-generate a reflection from an execution record."""
        succeeded = [s for s in execution_doc.get("step_results", []) if s.get("ok")]
        failed = [s for s in execution_doc.get("step_results", []) if not s.get("ok")]
        return ReflectionReport(
            organization_id=execution_doc["organization_id"],
            execution_id=execution_doc["execution_id"],
            subject_type="execution",
            subject_id=execution_doc["execution_id"],
            what_happened=f"Executed {len(execution_doc.get('steps', []))} steps for goal: "
                          f"{execution_doc.get('goal', '')}",
            why=f"Terminal status: {execution_doc.get('status', 'unknown')}",
            what_succeeded=[
                f"{s['capability_id']}: {', '.join(s.get('facts') or [])[:120]}"
                for s in succeeded
            ],
            what_failed=[f"{s['capability_id']}: {s.get('error') or 'policy blocked'}"
                         for s in failed],
            improvements=(
                ["Add higher-confidence pre-check before executing sensitive capabilities"]
                if failed else
                ["Consider parallelizing independent steps to reduce time-to-fill"]
            ),
            metrics={
                "steps_total": float(len(execution_doc.get("steps", []))),
                "steps_succeeded": float(len(succeeded)),
                "steps_failed": float(len(failed)),
            },
        )
