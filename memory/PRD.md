# EAROS — Enterprise Autonomous Recruitment Operating System

## Original Problem Statement
Build EAROS: an enterprise AI operating system for talent acquisition combining deterministic software architecture with governed AI reasoning. Every decision must be explainable, auditable, policy-governed. NOT an ATS. NOT a workflow automation. Separation of intelligence from execution. Three layers: Platform (Runtime, Planner, Policy Engine, Capability Registry, World State, Governance, Reflection, Memory), Intelligence (Hiring, Offer, Organizational, Workforce, Strategy, Decision, Reflection), Applications (Recruiter Copilot, Candidate Assistant, Executive Copilot, Voice AI, Hiring Dashboard).

## User Choices
- Scope: all three layers (Platform + Intelligence + Applications)
- Stack adaptation: Python/FastAPI + React + MongoDB
- LLM: Claude Sonnet 4.5 via emergentintegrations (Emergent Universal Key)
- Auth: Emergent-managed Google Auth
- Seed data: **LevelShift** org, jobs in India + USA, Salesforce/Dynamics/AI/Data Engineering/Sales/Client Partner roles

## Architecture (implemented)

```
/app/backend/
├── foundation/          # IDs, value objects, events, errors, result types
├── platform_core/       # Runtime, Planner, Policy, Capabilities, Memory, World, Governance, Reflection
├── intelligence/        # Hiring, Offer, Organizational, Workforce, Strategy
├── applications/        # Auth (Emergent Google), thin app endpoints
├── seed.py              # Idempotent LevelShift seed
└── server.py            # FastAPI wiring; every route delegates to platform+intelligence

/app/frontend/src/
├── App.js               # BrowserRouter + AuthProvider + Protected routes
├── contexts/AuthContext.jsx
├── components/
│   ├── layout/AppLayout.jsx        # Sidebar (APPS/INTELLIGENCE/PLATFORM), TopNav
│   └── ai/AIDecisionCard.jsx       # Canonical explainable AI card
├── pages/
│   ├── Landing.jsx
│   ├── AuthCallback.jsx
│   ├── HiringDashboard.jsx         # KPIs + charts + strategy
│   ├── RecruiterCopilot.jsx        # 3-pane: jobs / candidates / AI decisions + Planner + Runtime
│   ├── ExecutiveCopilot.jsx        # Org health + skill gaps + strategy card
│   ├── CandidateAssistant.jsx
│   ├── Governance.jsx              # Event stream + approval queue
│   ├── PolicyManager.jsx
│   ├── CapabilityRegistry.jsx
│   ├── WorldStateExplorer.jsx      # Tabbed org/departments/teams/jobs/candidates/offers/skills
│   ├── PlannerView.jsx             # Ad-hoc goal → LLM plan viewer
│   └── ReflectionReports.jsx
└── constants/testIds/earos.js
```

## Personas
- **Recruiter** — ranks candidates, drafts outreach, screens, schedules interviews (auto-approved by policy)
- **Hiring Manager** — reviews shortlists, approves stage advances above sensitivity threshold
- **Executive** — reads workforce intelligence, sets strategy, approves offers
- **Candidate** — checks status via candidate-safe assistant

## Core Requirements (static)
1. LLM never executes directly — flow: Planner → Runtime → Policy → Capability → World
2. Every AI recommendation carries reasoning + evidence + confidence + tradeoffs + risks + policy references
3. Immutable event stream for full replay + audit
4. Human approval mandatory for offers (policy-enforced)
5. First-class policy objects evaluated on every capability run

## What's Been Implemented (2026-01-10)
- **Foundation**: branded IDs, ConfidenceScore, Recommendation, DomainEvent, PolicyDecision, Sensitivity, Result[T]
- **Platform**: WorldState repo (org/depts/teams/skills/jobs/candidates/offers), CapabilityRegistry with 6 built-in capabilities (source, screen, advance_stage, draft_outreach, generate_offer, schedule_interview), PolicyEngine with 5 seeded policies, Runtime with retries + policy gating + event emission, Planner (Claude Sonnet 4.5 with deterministic fallback), Governance (audit + approvals), Reflection (auto-generated post-execution)
- **Intelligence**: cross-objective hiring ranking (skill/exp/salary/location/stage/risk composite), Offer intelligence with market percentile + parity delta + acceptance probability, Organizational health, Skill gap analysis, Hiring strategy
- **Applications**: Emergent Google Auth (session cookie + Bearer fallback + dev-login for demos), 10 UI pages (all with data-testids)
- **Seed**: 1 org (LevelShift), 5 depts, 9 teams, 32 skills, 12 jobs (6 India + 6 USA), 152 candidates, 5 policies, 3 demo users

## Verified end-to-end
- ✅ Backend seeds idempotently on startup
- ✅ Emergent Google Auth session flow (`/api/auth/session` + `/me` + `/logout` + `/dev-login`)
- ✅ Intelligence returns explainable recommendations (95% conf on top candidates)
- ✅ Planner returns valid JSON plans from Claude Sonnet 4.5 (with fallback)
- ✅ Runtime executes plans through policy gate; emits events; auto-generates reflection
- ✅ Frontend UI (Bloomberg/Foundry aesthetic) renders dashboards + AI decision cards

## Backlog (P1/P2 for future iterations)
- **P1** Voice AI interview capability (transcription + structured evaluation)
- **P1** Vector-embedding memory backend (currently keyword-scored stub)
- **P1** Parallel capability execution + dependency-graph runtime
- **P1** LLM streaming into UI (SSE) for planner + copilot chat
- **P2** Multi-tenant partitioning (currently designed for it, single-tenant seeded)
- **P2** Simulation mode (what-if) for headcount planning
- **P2** OpenTelemetry tracing hooks
- **P2** Fine-grained RBAC beyond role-string check

## Next Tasks
- Run testing_agent_v3 to validate end-to-end (auth-gated flows, intelligence, runtime, governance, approvals)
- Address any high/medium findings before finalizing
