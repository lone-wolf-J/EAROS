# EAROS Enterprise ATS Implementation Decision

## Decision

**EAROS remains the product and system of record.** The implementation will extend the existing React, FastAPI, and MongoDB application in place rather than merge its governed agent runtime into the parallel TalentFlow prototype.

This preserves the defining EAROS control plane: an AI planner may propose a grounded plan, but it cannot execute business actions. Every state-changing action must pass through the deterministic capability registry, organization-scoped policy evaluation, the human-approval gate where required, and the immutable governance event trail.

## Rationale

| Consideration | Decision impact |
| --- | --- |
| Product identity | The customer-facing product is named **EAROS**, so a separate TalentFlow system of record would create avoidable naming and workflow ambiguity. |
| Governed AI architecture | EAROS already separates planning, policy enforcement, runtime execution, approvals, and audit events. Rebuilding that architecture inside a different stack would introduce material delivery and assurance risk. |
| Existing ATS delivery | The parallel managed ATS implementation remains useful as a functional reference, but its records and screens will not be treated as a live source of truth for EAROS. |
| Tenant isolation | New repositories, API routes, capabilities, policies, and events must accept or derive an organization identifier and must filter by it on every read and write. |
| Human accountability | Outreach sends, job-board publication, stage transitions requiring exception handling, offer approvals, retention actions, and other sensitive actions remain approval-gated according to organization policy. |

## Operating Model

The enterprise ATS expansion is divided into three bounded layers.

| Layer | Responsibility | Constraint |
| --- | --- | --- |
| **World state** | Durable ATS records including requisitions, candidates, applications, interviews, feedback, offers, talent pools, consent, and retention metadata. | It contains factual, organization-scoped records; it does not allow a model to mutate data directly. |
| **Intelligence** | Resume extraction, matching, sourcing analysis, outreach drafts, interview preparation, and workflow recommendations. | It returns structured recommendations with evidence, confidence, risk, and provenance. |
| **Governed runtime** | Validates and executes registered deterministic capabilities, performs policy evaluation, pauses for approvals, records execution results, and emits immutable events. | It is the only state-changing execution route for autonomous actions. |

## Near-Term Scope

The first implementation increment establishes the canonical ATS objects and tenant-safe repository APIs: requisitions and hiring plans, reusable/custom pipelines, candidate profiles and deduplication keys, candidate-to-job applications, talent pools, consent records, resumes, interviews, scorecards, communication drafts, offers, and an append-only activity history. Each object will be designed so it can later be operated through a governed capability rather than bypassing the EAROS runtime.

## Explicit Non-Goals

This decision does not enable unattended scraping, unsupervised outreach delivery, automatic hiring or rejection decisions, opaque model-only scoring, or irreversible bulk retention deletion. Such actions require documented provider credentials, policy checks, human review where required, and auditable execution.
