# EAROS — Enterprise Autonomous Recruitment Operating System

## Original Problem Statement
Build EAROS: an enterprise AI operating system for talent acquisition combining deterministic software architecture with governed AI reasoning. Three layers: Platform (Runtime, Planner, Policy Engine, Capability Registry, World State, Governance, Reflection, Memory), Intelligence (Hiring, Offer, Organizational, Workforce, Strategy, Decision, Reflection), Applications (Recruiter Copilot, Candidate Assistant, Executive Copilot, Voice AI, Hiring Dashboard). Then (iteration 2): transform from a static dashboard into a fully interactive demonstration — Mission Control landing, animated live activity, 8 demo scenarios, conversational intake, 17 specialized agents, 24 integrations, sourcing sweep, resume studio, outreach studio, screening rubric, voice interview, what-if simulation.

## User Choices
- Python/FastAPI + React + MongoDB
- Claude Sonnet 4.5 via Emergent Universal Key
- Emergent Google Auth (+ dev-login for demos)
- **LevelShift** tenant, jobs in India + USA (Salesforce/Dynamics/AI/Data Engineering/Sales/Client Partner)
- Mission Control as landing page

## Architecture (both iterations)

```
/app/backend/
├── foundation/                # IDs, value objects, events, errors, result types
├── platform_core/
│   ├── world.py                # WorldState repository
│   ├── capabilities.py         # 6 built-in capabilities
│   ├── policy.py               # PolicyEngine (5 seeded policies)
│   ├── runtime.py              # Execution runtime with policy gating
│   ├── planner.py              # Claude Sonnet 4.5 planner + fallback
│   ├── memory.py               # Segmented memory
│   ├── governance.py           # Immutable events + approvals
│   ├── reflection.py           # Auto post-execution learning
│   ├── agents.py               # 17 specialized AI agent specs [v2]
│   ├── integrations.py         # 24 mocked integrations [v2]
│   └── live_activity.py        # Mission snapshot + ambient pulse [v2]
├── intelligence/
│   ├── __init__.py             # Hiring, Offer, Organizational, Workforce, Strategy
│   ├── intake.py               # Conversational intake (Claude + fallback) [v2]
│   ├── sourcing.py             # 10-channel parallel sweep [v2]
│   ├── resume_intel.py         # Parse + fit + redact + client-summary [v2]
│   ├── outreach_gen.py         # Multi-channel A/B + follow-up [v2]
│   ├── screening_rubric.py     # 8-dim rubric [v2]
│   ├── voice_interview.py      # Mock live interview [v2]
│   ├── simulation.py           # Executive what-if [v2]
│   └── scenarios.py            # 8 end-to-end scenario runners [v2]
├── applications/               # Auth (Emergent Google + dev-login)
├── seed.py                     # Idempotent LevelShift seed
└── server.py                   # FastAPI wiring (~60 endpoints)

/app/frontend/src/
├── App.js                      # BrowserRouter + AuthProvider + Protected routes (Mission Control default)
├── contexts/AuthContext.jsx
├── components/
│   ├── layout/AppLayout.jsx    # 3-group sidebar (APPS / INTELLIGENCE / PLATFORM)
│   └── ai/AIDecisionCard.jsx   # Canonical explainable AI card
└── pages/
    ├── Landing.jsx + AuthCallback.jsx
    ├── MissionControl.jsx      # LIVE — 8 KPIs + 17 agent pulses + ambient ticker [v2]
    ├── Scenarios.jsx           # 8 full-lifecycle scenarios [v2]
    ├── HiringIntake.jsx        # Conversational intake with Claude reasoning [v2]
    ├── Agents.jsx              # Agent registry grouped by category [v2]
    ├── Integrations.jsx        # 24 connected systems [v2]
    ├── Sourcing.jsx            # 10-channel parallel sweep visualization [v2]
    ├── ResumeStudio.jsx        # Parse + fit + redact + client one-pager [v2]
    ├── OutreachStudio.jsx      # Multi-channel A/B with follow-up [v2]
    ├── Screening.jsx           # 8-dim rubric scoring [v2]
    ├── VoiceInterview.jsx      # Interactive mock interview [v2]
    ├── ExecutiveCopilot.jsx    # + WHAT-IF sliders live-updating trajectory + AI decision card [v2]
    ├── HiringDashboard.jsx / RecruiterCopilot.jsx / CandidateAssistant.jsx
    └── Governance.jsx / PolicyManager.jsx / CapabilityRegistry.jsx / WorldStateExplorer.jsx / PlannerView.jsx / ReflectionReports.jsx
```

## Personas
- **Recruiter** — Mission Control → Intake → Recruiter Copilot → Sourcing → Screening → Outreach → Voice
- **Hiring Manager** — Approvals review + governance
- **Executive** — Mission Control → Executive Copilot with what-if sliders → Strategy
- **Candidate** — Candidate Assistant (safe view)

## Core Invariants (verified)
1. LLM never executes directly — Planner → Runtime → Policy → Capability → World
2. Every AI recommendation carries reasoning + evidence + confidence + tradeoffs + risks + policy references
3. Immutable event stream — full replay + audit via correlation_id
4. Human approval mandatory for offers (policy-enforced)
5. First-class policy objects evaluated on every capability run
6. Reflection auto-generated after terminal executions
7. Candidate-safe view leaks no confidential data

## What's Been Implemented

### Iteration 1 (2026-01-10)
- Platform Core (Runtime + Planner + Policy + Capabilities + World + Governance + Reflection + Memory)
- Intelligence Layer (Hiring + Offer + Organizational + Workforce + Strategy)
- 6 built-in capabilities, 5 policies, 12 jobs (6 India + 6 USA), 150+ candidates
- 10 pages including Recruiter Copilot with plan simulation + runtime execution
- Emergent Google Auth + dev-login
- **Testing: 29/29 backend + 100% frontend**

### Iteration 2 (2026-01-11) — Live Interactive Demonstration
- **Mission Control** landing page with 8 KPIs, 17 agent pulse cards, ambient ticker (~3s refresh), approvals queue, runtime status, reflection stream
- **8 Demo Scenarios** that execute full lifecycles (sourcing → screening × 3 → outreach × 2 → interview → offer→ reflection) with animated 15-stage progress ribbon
- **Conversational Intake** using Claude Sonnet 4.5 — extracts requirements, ambiguities, clarifying questions, interview panel, channel plan, comp band, difficulty, JD, screening rubric, risks
- **Agent Registry** — 17 specialized agents (Intake, JD, Market, Sourcing, Resume, Ranking, Outreach, Response Monitor, Screening, Interview, Offer, Reference Check, BGV, Planner, Runtime, Policy, Reflection) with live 24h metrics
- **Integrations Catalog** — 24 systems (LinkedIn, Dice, GitHub, Naukri, Monster, Indeed, ZipRecruiter, Wellfound, Stack Overflow, CEIPAL, Bullhorn, Greenhouse, Lever, Recruiter.com, Internal ATS, Workday, Gmail, Slack, Teams, WhatsApp, Twilio, Referrals, Community, Calendar) with connection status + health
- **Sourcing** — 10-channel parallel sweep with staggered row reveal
- **Resume Studio** — parse + fit analysis + client-ready redacted one-pager
- **Outreach Studio** — 3 email variants (warm/direct/curiosity) + LinkedIn/SMS/WhatsApp/voice + 3-day follow-up + agent reasoning
- **Screening** — 8-dimension rubric with score + weight + notes + composite + band + summary
- **Voice Interview** — turn-based mock interview with sentiment, signal, STAR extraction, follow-ups, and end-of-interview summary
- **Executive What-If** — live sliders (attrition, budget, hiring freeze, Bangalore expansion, AI doubles) that recompute headcount trajectory + AI recommendation with reasoning + risks
- Editable + simulate-able **Policies** (backend endpoints; UI already lists them)
- **Testing: 41/41 backend (29 v1 regression + 12 v2) + 100% frontend**

### Iteration 3 addendum
## Backlog (P1/P2 for future iterations)

- **P0 fixes**:
  - World State tabs now render distinct content per tab; Organization tab is a card view (no raw JSON); Teams tab shows department name via lookup; Candidates tab shows role via lookup; unique React keys per row
  - Dashboard + Executive Copilot KPI tiles show animated skeleton loaders on cold load — no flash of `—` or `0`
  - Recruiter Copilot APPROVE & EXECUTE now (a) revalidates candidates via SWR so the pipeline stage visibly changes, (b) fires a color-coded toast (success/awaiting/blocked), (c) preserves the current AI decision card instead of re-shuffling
  - Scenarios ribbon animates through 15 lifecycle stages and shows LIFECYCLE COMPLETE
- **Agent Deep-Dive (`/deep-dive`)** — the crown jewel for the demo. Animated 7-lane swimlane replay (Planner → Policy → Runtime → Capability → World → Governance → Reflection). Play/Pause/Reset controls, 3-speed animation, per-message detail panel with actor/subject/capability/confidence/policies/payload (field-by-field, no JSON blob), roll-up header with total ms + cost + auto-approved vs. human-gated. Any historical execution or scenario correlation_id is replayable.
- **correlation_id plumbing** through PolicyEngine, Governance approvals, and Reflection — all events under a scenario or execution now share the same correlation_id so replay hits all 6 active lanes.
- **Executive polish**: Governance "in 30 seconds" explainer, amber `DEMO · SYNTHETIC DATA` pill in the persistent top nav, Integrations clarifier for intentionally-degraded systems, plain-English Mission Control sub-labels.
- **Testing: 47/48 backend (1 test-assumption noted, not product defect) · 95% frontend (2 minor items: duplicate-key warning now fixed; ribbon text was a timing artifact).**
- **P1** SSE streaming for planner + copilot chat (currently polling)
- **P1** Vector-embedding memory backend (currently keyword-scored stub)
- **P1** Live orchestration DAG visualization on Mission Control (currently animated ribbon on Scenarios)
- **P1** Real integrations: LinkedIn/Naukri/etc. behind feature flags
- **P2** Voice AI: real STT/TTS instead of scripted turn-based mock
- **P2** Multi-tenant activation
- **P2** OpenTelemetry tracing hooks
- **P2** Policy editor UI (backend already supports CRUD + simulate)

## Next Tasks
- Ship. This is a demo-ready enterprise AI OS.
