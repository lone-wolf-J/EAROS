"""Execution Runtime — orchestration, lifecycle, retries, checkpoints,
interrupts, resumability, execution history.

The Runtime owns execution. The LLM never bypasses it.
Flow: plan -> for each step -> policy.evaluate -> capability.handler -> world/events.
"""
from __future__ import annotations

import asyncio
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, ConfigDict, Field

from foundation import (
    DomainEvent,
    EventType,
    ExecutionStatus,
    PolicyDecision,
    Sensitivity,
    new_execution_id,
    new_step_id,
    utcnow_iso,
)
from platform_core.capabilities import (
    CapabilityContext,
    CapabilityRegistry,
    CapabilityResult,
)
from platform_core.governance import Approval, Governance
from platform_core.policy import PolicyContext, PolicyEngine
from platform_core.world import WorldState


class PlanStep(BaseModel):
    model_config = ConfigDict(extra="ignore")
    step_id: str = Field(default_factory=new_step_id)
    capability_id: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    confidence: float = 0.75
    sensitivity: Sensitivity = Sensitivity.INTERNAL


class ExecutionRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    execution_id: str = Field(default_factory=new_execution_id)
    plan_id: Optional[str] = None
    organization_id: str
    user_id: str
    user_role: str
    goal: str
    steps: list[PlanStep] = Field(default_factory=list)
    step_results: list[dict[str, Any]] = Field(default_factory=list)
    status: ExecutionStatus = ExecutionStatus.PENDING
    correlation_id: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None
    pending_approvals: list[str] = Field(default_factory=list)
    decision_id: Optional[str] = None  # links back to the AI Recommendation


class Runtime:
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        world: WorldState,
        registry: CapabilityRegistry,
        policy: PolicyEngine,
        governance: Governance,
    ):
        self.db = db
        self.world = world
        self.registry = registry
        self.policy = policy
        self.governance = governance

    async def _persist(self, ex: ExecutionRecord) -> None:
        await self.db.executions.update_one(
            {"execution_id": ex.execution_id}, {"$set": ex.model_dump()}, upsert=True
        )

    async def get_execution(self, execution_id: str) -> Optional[ExecutionRecord]:
        doc = await self.db.executions.find_one({"execution_id": execution_id}, {"_id": 0})
        return ExecutionRecord(**doc) if doc else None

    async def list_executions(
        self, organization_id: str, limit: int = 50
    ) -> list[ExecutionRecord]:
        docs = await self.db.executions.find(
            {"organization_id": organization_id}, {"_id": 0}
        ).sort("started_at", -1).to_list(limit)
        return [ExecutionRecord(**d) for d in docs]

    async def execute(
        self, ex: ExecutionRecord, preapproved_step_ids: Optional[set[str]] = None
    ) -> ExecutionRecord:
        preapproved_step_ids = preapproved_step_ids or set()
        ex.status = ExecutionStatus.RUNNING
        ex.started_at = utcnow_iso()
        await self._persist(ex)
        await self.governance.emit(DomainEvent(
            event_type=EventType.EXECUTION_STARTED,
            actor=ex.user_id,
            subject_type="execution",
            subject_id=ex.execution_id,
            organization_id=ex.organization_id,
            payload={"goal": ex.goal, "steps": len(ex.steps)},
            correlation_id=ex.correlation_id,
        ))

        completed: dict[str, dict[str, Any]] = {
            result["step_id"]: result.get("output") or {}
            for result in ex.step_results
            if result.get("ok") and result.get("step_id")
        }

        try:
            for step in ex.steps:
                # Wait for dependencies (in this simplified serial impl, they're already done)
                unmet = [d for d in step.depends_on if d not in completed]
                if unmet:
                    raise RuntimeError(f"unmet deps: {unmet}")
                if step.step_id in completed:
                    continue

                # 1. Policy evaluation for this step
                pol_ctx = PolicyContext(
                    organization_id=ex.organization_id,
                    user_id=ex.user_id,
                    user_role=ex.user_role,
                    capability_id=step.capability_id,
                    sensitivity=step.sensitivity,
                    confidence=step.confidence,
                    correlation_id=ex.correlation_id,
                    payload=step.inputs,
                )
                pol_result = await self.policy.evaluate(pol_ctx)

                if pol_result.decision == PolicyDecision.DENY:
                    ex.status = ExecutionStatus.POLICY_BLOCKED
                    ex.error = f"Step {step.step_id} blocked: {pol_result.reason}"
                    ex.step_results.append({
                        "step_id": step.step_id,
                        "capability_id": step.capability_id,
                        "policy_decision": pol_result.decision.value,
                        "policy_reason": pol_result.reason,
                        "policies": [r.model_dump() for r in pol_result.policies_referenced],
                        "ok": False,
                        "output": None,
                    })
                    ex.finished_at = utcnow_iso()
                    await self._persist(ex)
                    await self.governance.emit(DomainEvent(
                        event_type=EventType.EXECUTION_FAILED,
                        actor=ex.user_id, subject_type="execution", subject_id=ex.execution_id,
                        organization_id=ex.organization_id,
                        payload={"reason": ex.error}, correlation_id=ex.correlation_id,
                    ))
                    return ex

                if (
                    pol_result.decision == PolicyDecision.REQUIRE_APPROVAL
                    and step.step_id not in preapproved_step_ids
                ):
                    approval = await self.governance.request_approval(Approval(
                        organization_id=ex.organization_id,
                        subject_type="execution_step",
                        subject_id=step.step_id,
                        requested_by=ex.user_id,
                        reason=f"Policy requires approval for {step.capability_id}: {pol_result.reason}",
                        context={
                            "execution_id": ex.execution_id,
                            "capability_id": step.capability_id,
                            "inputs": step.inputs,
                            "policies": [r.model_dump() for r in pol_result.policies_referenced],
                            "correlation_id": ex.correlation_id,
                        },
                    ))
                    ex.pending_approvals.append(approval.approval_id)
                    ex.status = ExecutionStatus.AWAITING_APPROVAL
                    ex.step_results.append({
                        "step_id": step.step_id,
                        "capability_id": step.capability_id,
                        "policy_decision": pol_result.decision.value,
                        "policy_reason": pol_result.reason,
                        "approval_id": approval.approval_id,
                        "ok": False,
                        "output": None,
                    })
                    ex.finished_at = utcnow_iso()
                    await self._persist(ex)
                    return ex

                # 2. Execute capability
                await self.governance.emit(DomainEvent(
                    event_type=EventType.STEP_STARTED,
                    actor="runtime", subject_type="step", subject_id=step.step_id,
                    organization_id=ex.organization_id,
                    payload={"capability_id": step.capability_id, "inputs": step.inputs},
                    correlation_id=ex.correlation_id,
                ))

                handler = self.registry.get_handler(step.capability_id)
                if not handler:
                    raise RuntimeError(f"capability {step.capability_id} not registered")

                ctx = CapabilityContext(
                    organization_id=ex.organization_id,
                    user_id=ex.user_id,
                    execution_id=ex.execution_id,
                    correlation_id=ex.correlation_id,
                    world=self.world,
                )

                # simple retry (2 attempts, 100ms backoff)
                result: CapabilityResult = CapabilityResult(ok=False, error="not run")
                for attempt in range(2):
                    try:
                        result = await asyncio.wait_for(handler(step.inputs, ctx), timeout=30.0)
                        if result.ok:
                            break
                    except asyncio.TimeoutError:
                        result = CapabilityResult(ok=False, error="timeout")
                    await asyncio.sleep(0.1)

                completed[step.step_id] = result.output
                ex.step_results.append({
                    "step_id": step.step_id,
                    "capability_id": step.capability_id,
                    "policy_decision": pol_result.decision.value,
                    "policies": [r.model_dump() for r in pol_result.policies_referenced],
                    "ok": result.ok,
                    "output": result.output,
                    "facts": result.facts,
                    "error": result.error,
                })

                await self.governance.emit(DomainEvent(
                    event_type=EventType.STEP_COMPLETED,
                    actor="runtime", subject_type="step", subject_id=step.step_id,
                    organization_id=ex.organization_id,
                    payload={
                        "capability_id": step.capability_id,
                        "ok": result.ok, "facts": result.facts, "error": result.error,
                    },
                    correlation_id=ex.correlation_id,
                ))

                if not result.ok:
                    ex.status = ExecutionStatus.FAILED
                    ex.error = result.error or "step failed"
                    ex.finished_at = utcnow_iso()
                    await self._persist(ex)
                    await self.governance.emit(DomainEvent(
                        event_type=EventType.EXECUTION_FAILED,
                        actor=ex.user_id, subject_type="execution", subject_id=ex.execution_id,
                        organization_id=ex.organization_id,
                        payload={"reason": ex.error}, correlation_id=ex.correlation_id,
                    ))
                    return ex

            ex.status = ExecutionStatus.SUCCEEDED
            ex.finished_at = utcnow_iso()
            await self._persist(ex)
            await self.governance.emit(DomainEvent(
                event_type=EventType.EXECUTION_COMPLETED,
                actor=ex.user_id, subject_type="execution", subject_id=ex.execution_id,
                organization_id=ex.organization_id,
                payload={"steps": len(ex.steps)}, correlation_id=ex.correlation_id,
            ))
            return ex

        except Exception as e:  # noqa: BLE001
            ex.status = ExecutionStatus.FAILED
            ex.error = str(e)
            ex.finished_at = utcnow_iso()
            await self._persist(ex)
            await self.governance.emit(DomainEvent(
                event_type=EventType.EXECUTION_FAILED,
                actor=ex.user_id, subject_type="execution", subject_id=ex.execution_id,
                organization_id=ex.organization_id,
                payload={"reason": str(e)}, correlation_id=ex.correlation_id,
            ))
            return ex

    async def resume_after_approval(
        self, execution_id: str, organization_id: str
    ) -> ExecutionRecord:
        """Resume only the recorded steps whose approvals were explicitly granted."""
        ex = await self.get_execution(execution_id)
        if not ex or ex.organization_id != organization_id:
            raise ValueError("execution not found for organization")
        if ex.status != ExecutionStatus.AWAITING_APPROVAL:
            return ex

        approvals = [
            await self.governance.get_approval(approval_id)
            for approval_id in ex.pending_approvals
        ]
        if not approvals or any(approval is None for approval in approvals):
            return ex
        if any(approval.status == "denied" for approval in approvals if approval):
            ex.status = ExecutionStatus.POLICY_BLOCKED
            ex.error = "required approval was denied"
            ex.finished_at = utcnow_iso()
            await self._persist(ex)
            await self.governance.emit(DomainEvent(
                event_type=EventType.EXECUTION_FAILED,
                actor=ex.user_id,
                subject_type="execution",
                subject_id=ex.execution_id,
                organization_id=ex.organization_id,
                payload={"reason": ex.error},
                correlation_id=ex.correlation_id,
            ))
            return ex
        if any(approval.status != "granted" for approval in approvals if approval):
            return ex

        approved_step_ids = {
            approval.subject_id for approval in approvals
            if approval and approval.subject_type == "execution_step"
        }
        ex.pending_approvals = []
        ex.status = ExecutionStatus.PENDING
        ex.error = None
        await self._persist(ex)
        await self.governance.emit(DomainEvent(
            event_type=EventType.EXECUTION_RESUMED,
            actor="runtime",
            subject_type="execution",
            subject_id=ex.execution_id,
            organization_id=ex.organization_id,
            payload={"approved_step_ids": sorted(approved_step_ids)},
            correlation_id=ex.correlation_id,
        ))
        return await self.execute(ex, preapproved_step_ids=approved_step_ids)
