"""Scenario execution tracker — an in-memory state machine that lets the
frontend watch a scenario progress step-by-step with pacing and approval
gates. This is what makes the executive demo feel alive.

Each execution is tracked as a ScenarioExecutionState. The frontend polls
`/api/scenarios/executions/{id}/state` every ~700ms and renders the
current step, progress %, and any pending approval gate.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


# Timings tuned for a live demo: fast enough not to bore, slow enough for
# executives to read the label and understand what the agent is doing.
STEP_PACE_SECONDS = 1.7          # baseline delay between steps
APPROVAL_TIMEOUT_SECONDS = 600   # 10 minutes — plenty of time for a live click.
                                 # If it times out, the scenario is CANCELLED,
                                 # not silently auto-approved.


@dataclass
class ScenarioStep:
    key: str
    label: str
    agent: str          # e.g. "Sourcing Agent"
    detail: str         # e.g. "Scanning GitHub, LinkedIn, Dice for Java + Kafka"
    status: str = "pending"   # pending | running | done | skipped
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    output: Optional[str] = None


@dataclass
class ScenarioExecutionState:
    execution_id: str
    scenario_id: str
    scenario_title: str
    correlation_id: Optional[str] = None
    status: str = "running"     # running | awaiting_approval | completed | failed | cancelled
    steps: list[ScenarioStep] = field(default_factory=list)
    current_step_idx: int = 0
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    ended_at: Optional[str] = None
    error: Optional[str] = None

    # Approval gate
    approval: Optional[dict[str, Any]] = None  # {"reason","subject","expires_at","seconds_remaining"}

    # Final result payload (populated on completion)
    result: Optional[dict[str, Any]] = None

    # Runtime primitives (never serialised)
    _approval_event: Optional[asyncio.Event] = field(default=None, repr=False)
    _approval_decision: Optional[str] = field(default=None, repr=False)   # "approved" | "rejected"
    _approval_deadline: Optional[float] = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        approval = None
        if self.approval and self._approval_deadline is not None:
            remaining = max(0.0, self._approval_deadline - asyncio.get_event_loop().time())
            approval = {
                **self.approval,
                "seconds_remaining": round(remaining, 1),
            }
        return {
            "execution_id": self.execution_id,
            "scenario_id": self.scenario_id,
            "scenario_title": self.scenario_title,
            "correlation_id": self.correlation_id,
            "status": self.status,
            "current_step_idx": self.current_step_idx,
            "total_steps": len(self.steps),
            "progress_pct": (
                int(100 * self.current_step_idx / max(1, len(self.steps)))
                if self.status != "completed"
                else 100
            ),
            "steps": [s.__dict__ for s in self.steps],
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "error": self.error,
            "approval": approval,
            "result": self.result,
        }


class ScenarioTracker:
    """Singleton-style tracker keeping in-memory state for running scenarios."""

    def __init__(self) -> None:
        self._executions: dict[str, ScenarioExecutionState] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    def create(self, scenario_id: str, scenario_title: str,
               step_defs: list[tuple[str, str, str, str]]) -> ScenarioExecutionState:
        """Create a fresh execution. step_defs is a list of
        (key, label, agent, detail) tuples."""
        exec_id = f"exe_{uuid.uuid4().hex[:12]}"
        state = ScenarioExecutionState(
            execution_id=exec_id,
            scenario_id=scenario_id,
            scenario_title=scenario_title,
            steps=[ScenarioStep(key=k, label=l, agent=a, detail=d)
                   for (k, l, a, d) in step_defs],
        )
        self._executions[exec_id] = state
        return state

    def get(self, execution_id: str) -> Optional[ScenarioExecutionState]:
        return self._executions.get(execution_id)

    def attach_task(self, execution_id: str, task: asyncio.Task) -> None:
        self._tasks[execution_id] = task

    async def start_step(self, execution_id: str, key: str) -> None:
        state = self._executions.get(execution_id)
        if not state:
            return
        for idx, step in enumerate(state.steps):
            if step.key == key:
                step.status = "running"
                step.started_at = datetime.now(timezone.utc).isoformat()
                state.current_step_idx = idx
                return

    async def complete_step(self, execution_id: str, key: str,
                             output: Optional[str] = None) -> None:
        state = self._executions.get(execution_id)
        if not state:
            return
        for step in state.steps:
            if step.key == key:
                step.status = "done"
                step.ended_at = datetime.now(timezone.utc).isoformat()
                if output:
                    step.output = output
                return

    async def request_approval(self, execution_id: str, subject: str,
                                reason: str) -> str:
        """Pause execution and wait for approve/reject or timeout."""
        state = self._executions.get(execution_id)
        if not state:
            return "cancelled"

        loop = asyncio.get_event_loop()
        state.status = "awaiting_approval"
        state._approval_event = asyncio.Event()
        state._approval_deadline = loop.time() + APPROVAL_TIMEOUT_SECONDS
        state.approval = {
            "subject": subject,
            "reason": reason,
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "timeout_seconds": APPROVAL_TIMEOUT_SECONDS,
        }

        try:
            await asyncio.wait_for(
                state._approval_event.wait(),
                timeout=APPROVAL_TIMEOUT_SECONDS,
            )
            decision = state._approval_decision or "cancelled"
        except asyncio.TimeoutError:
            decision = "timed_out_cancelled"

        state.approval = None
        state._approval_deadline = None
        if state.status == "awaiting_approval":
            state.status = "running"
        return decision

    def approve(self, execution_id: str) -> bool:
        state = self._executions.get(execution_id)
        if not state or state.status != "awaiting_approval":
            return False
        state._approval_decision = "approved"
        if state._approval_event:
            state._approval_event.set()
        return True

    def reject(self, execution_id: str) -> bool:
        state = self._executions.get(execution_id)
        if not state or state.status != "awaiting_approval":
            return False
        state._approval_decision = "rejected"
        if state._approval_event:
            state._approval_event.set()
        return True

    def finish(self, execution_id: str, result: dict[str, Any]) -> None:
        state = self._executions.get(execution_id)
        if not state:
            return
        state.status = "completed"
        state.ended_at = datetime.now(timezone.utc).isoformat()
        state.current_step_idx = len(state.steps)
        state.result = result
        for step in state.steps:
            if step.status == "pending":
                step.status = "skipped"

    def fail(self, execution_id: str, error: str) -> None:
        state = self._executions.get(execution_id)
        if not state:
            return
        state.status = "failed"
        state.error = error
        state.ended_at = datetime.now(timezone.utc).isoformat()


# Module-level singleton
tracker = ScenarioTracker()
