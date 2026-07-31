"""Policy Engine — first-class policy objects.

Policies evaluate: user, organization, role, capability, sensitivity,
compliance, cost, confidence, required approvals.

Every evaluation returns an immutable audit record.
"""
from __future__ import annotations

from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, ConfigDict, Field

from foundation import (
    DomainEvent,
    EventType,
    PolicyDecision,
    PolicyReference,
    Sensitivity,
    new_policy_id,
    utcnow_iso,
)
from platform_core.governance import Governance


class Policy(BaseModel):
    model_config = ConfigDict(extra="ignore")
    policy_id: str = Field(default_factory=new_policy_id)
    name: str
    description: str
    scope: str  # capability_id or "*"
    applies_to_roles: list[str] = Field(default_factory=lambda: ["*"])
    required_role_for_approval: Optional[str] = None
    max_sensitivity: Optional[str] = None
    min_confidence: Optional[float] = None
    requires_human_approval: bool = False
    enabled: bool = True
    version: int = 1
    created_at: str = Field(default_factory=utcnow_iso)


class PolicyContext(BaseModel):
    organization_id: str
    user_id: str
    user_role: str
    capability_id: str
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    confidence: Optional[float] = None
    cost_estimate: float = 0.0
    correlation_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)


class PolicyEvaluationResult(BaseModel):
    decision: PolicyDecision
    policies_referenced: list[PolicyReference] = Field(default_factory=list)
    reason: str
    requires_approval: bool = False


class PolicyEngine:
    def __init__(self, db: AsyncIOMotorDatabase, governance: Governance):
        self.db = db
        self.governance = governance

    async def upsert_policy(self, p: Policy) -> Policy:
        await self.db.policies.update_one(
            {"policy_id": p.policy_id}, {"$set": p.model_dump()}, upsert=True
        )
        return p

    async def list_policies(self) -> list[Policy]:
        docs = await self.db.policies.find({}, {"_id": 0}).to_list(500)
        return [Policy(**d) for d in docs]

    async def get_policy(self, policy_id: str) -> Optional[Policy]:
        doc = await self.db.policies.find_one({"policy_id": policy_id}, {"_id": 0})
        return Policy(**doc) if doc else None

    async def evaluate(self, ctx: PolicyContext) -> PolicyEvaluationResult:
        """Evaluate all applicable policies for the given context.

        The default posture is ALLOW unless any policy DENIES or requires approval.
        """
        policies = await self.list_policies()
        refs: list[PolicyReference] = []
        deny_reasons: list[str] = []
        require_approval = False
        approval_reasons: list[str] = []

        for p in policies:
            if not p.enabled:
                continue
            if p.scope != "*" and p.scope != ctx.capability_id:
                continue
            if "*" not in p.applies_to_roles and ctx.user_role not in p.applies_to_roles:
                continue

            policy_decision = PolicyDecision.ALLOW
            reason_bits: list[str] = []

            # sensitivity ceiling
            if p.max_sensitivity:
                order = ["public", "internal", "confidential", "restricted"]
                if order.index(ctx.sensitivity.value) > order.index(p.max_sensitivity):
                    policy_decision = PolicyDecision.DENY
                    reason_bits.append(
                        f"sensitivity {ctx.sensitivity.value} exceeds allowed {p.max_sensitivity}"
                    )

            # min confidence gate
            if p.min_confidence is not None and ctx.confidence is not None:
                if ctx.confidence < p.min_confidence:
                    policy_decision = PolicyDecision.REQUIRE_APPROVAL
                    reason_bits.append(
                        f"confidence {ctx.confidence:.2f} below required {p.min_confidence:.2f}"
                    )

            # explicit human approval requirement
            if p.requires_human_approval:
                policy_decision = (
                    PolicyDecision.DENY if policy_decision == PolicyDecision.DENY
                    else PolicyDecision.REQUIRE_APPROVAL
                )
                reason_bits.append("human approval required by policy")

            refs.append(PolicyReference(
                policy_id=p.policy_id,
                name=p.name,
                decision=policy_decision,
                reason="; ".join(reason_bits) if reason_bits else "ok",
            ))

            if policy_decision == PolicyDecision.DENY:
                deny_reasons.extend(reason_bits)
            elif policy_decision == PolicyDecision.REQUIRE_APPROVAL:
                require_approval = True
                approval_reasons.extend(reason_bits)

        # Aggregate the per-policy decisions. Defaults keep static analyzers
        # (and any future refactor that shortens the if/elif/else) safe.
        final = PolicyDecision.ALLOW
        reason = "all policies passed"
        if deny_reasons:
            final = PolicyDecision.DENY
            reason = "; ".join(deny_reasons)
        elif require_approval:
            final = PolicyDecision.REQUIRE_APPROVAL
            reason = "; ".join(approval_reasons) or "approval required"

        # Emit immutable audit event
        await self.governance.emit(DomainEvent(
            event_type=(
                EventType.POLICY_VIOLATED if final == PolicyDecision.DENY
                else EventType.POLICY_EVALUATED
            ),
            actor=ctx.user_id,
            subject_type="capability",
            subject_id=ctx.capability_id,
            organization_id=ctx.organization_id,
            payload={
                "decision": final.value,
                "reason": reason,
                "policies": [r.model_dump() for r in refs],
                "confidence": ctx.confidence,
                "sensitivity": ctx.sensitivity.value,
                "capability_id": ctx.capability_id,
            },
            correlation_id=ctx.correlation_id,
        ))

        return PolicyEvaluationResult(
            decision=final,
            policies_referenced=refs,
            reason=reason,
            requires_approval=(final == PolicyDecision.REQUIRE_APPROVAL),
        )
