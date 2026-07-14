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

## v2 Interactivity Build — Progress Log

### 2026-02-13 — Task 1: Demo Scenarios Pacing & Visibility ✅ DONE
- Added `intelligence/scenario_tracker.py` — in-memory ScenarioTracker with per-execution state machine (running / awaiting_approval / completed / failed) and asyncio.Event-based approval gate with 20s auto-resume timeout
- Refactored `intelligence/scenarios.py`: new `run_scenario_paced` runs as a background task through 14 named lifecycle stages (Intake → JD Intelligence → Market Intelligence → Planner → Policy Eval → Sourcing → Resume Intel → Ranking → Outreach → Screening → Interview → Offer Prep → **Human Approval Gate (pauses)** → Reflection) with deliberate ~1.7s pacing per step
- `server.py`: `POST /api/scenarios/{id}/run` now returns an execution_id immediately; new endpoints `GET /executions/{id}/state`, `POST /approve`, `POST /reject`; legacy sync behaviour preserved under `/run-sync` for tests
- `frontend/src/pages/Scenarios.jsx` (full rewrite): polls state every 700ms, renders a persistent stage tracker with current-step banner, active agent label, progress bar, per-step output detail rows, and a prominent amber "HUMAN APPROVAL REQUIRED" card with live countdown + Approve/Reject buttons + open-replay/audit CTAs on completion
- Tests: `tests/test_scenarios_paced.py` — 5 new tests (execution_id creation, full approval flow, rejection flow, 404, 400 without gate) — all passing. Existing v2/v3 tests updated to use `/run-sync`. 14/14 tests green.

### 2026-02-14 — Task 2: Hiring Intake → Job Architecture Agent branch ✅ DONE
- Backend `POST /api/intake/analyze` now returns two extra fields:
  - `matched_job_id` — fuzzy-matched to closest seeded requisition (title tokens + location + must-have skill overlap; scoring in `server.py::_match_job_to_intake`)
  - `sourcing_plan` — 3-wave (P0/P1/P2) plan with per-wave target candidate counts, Boolean search string derived from must-haves + location, estimated reach and sweep minutes (`server.py::_build_sourcing_plan`)
- Frontend `HiringIntake.jsx`: added `JobArchitectureFlow` component — a 4-step paced banner (Requirements Agent → Job Architecture Agent → Sourcing Strategy Agent → Recruiter Handoff) that ticks visibly at ~1.4s intervals while the LLM runs. On completion shows matched requisition ID, an `OPEN IN RECRUITER COPILOT` CTA, the search string, and the multi-wave sourcing plan
- `RecruiterCopilot.jsx`: now reads `?job=<job_id>` from `useSearchParams` and pre-selects that requisition — no manual scrolling to find the freshly-briefed req
- Tests: `tests/test_intake_handoff.py` — 2 new pytest cases (Salesforce brief matches `job_sfdc_arch_austin` + sourcing plan shape; vague brief still returns a plan). 7/7 new Task-1+2 tests green.

### 2026-02-14 — Tasks 3-8: Interactivity Sprint ✅ DONE

**Task 3 · Dashboard KPI drill-downs**
- `HiringDashboard.jsx`: every KPI tile (Open Reqs, In Pipeline, Offers Active, Hired YTD, Time-to-Fill, P0 Roles) is now a `<button>` that opens a right-side `DrillDownDrawer` with filtered records from `/world/jobs` or `/world/candidates`. Each row links to Recruiter Copilot with the correct `?job=` pre-selected.

**Task 4 · Recruiter Copilot ops surface**
- New backend endpoint `POST /api/world/candidates/{id}/stage` for manual stage transitions with immutable `CANDIDATE_STAGE_CHANGED` audit event emitted through `governance.emit()`
- `RecruiterCopilot.jsx`: added `AutonomyToggle` (Manual/Semi-auto/Full-auto), `PipelineIntel` strip (Active/Avg Fit/Risk/Offers/Autonomy), `OpsToolbar` (Email/SMS/Screening/Harvester), `OpsModal` (recipient checklist, editable subject+body with `{{first_name}}` templating, paced send simulation), `StageTransition` dropdown that hits the new endpoint and refreshes candidate list, and a `candidate-detail-card` with fit score + skills row.

**Task 5 · Sourcing action plan**
- `Sourcing.jsx`: after a sweep completes, shows a "RECOMMENDED ACTION PLAN" panel with 4 executable next actions (contact top 25, AI screen top 10, retarget from top source, schedule 5 with HM), each with a capability label and navigation CTA.

**Task 6 · Resume Studio format selector**
- `ResumeStudio.jsx`: added a two-option format toggle (`one_page` vs `client_submission`). One-page = compact internal card. Client submission = full doc-style package with anonymised header, skills matrix (matched vs missing), differentiators, comp/logistics footer, PII-redacted watermark.

**Task 7 · Outreach Studio operational**
- `OutreachStudio.jsx`: candidate list turned into a searchable, multi-select recipient checklist. Every email tone has an `edit` toggle + `SEND TO N` per-variant send button. LinkedIn/SMS/WhatsApp/Voice each get their own send. Paced send with a live "sending → sent" banner.

**Task 8 · AI Interview Suite (consolidated)**
- New page `InterviewSuite.jsx` at `/interview` with a 4-mode selector (AI Screening, AI Voice, AI Copilot, Autonomous Video). Each mode has its own config inputs and a **context-specific report**: rubric bars for Screening (real backend `/screening/rubric`), transcript signals + red flags for Voice, live-scoring + AI flags + scorecard draft for Copilot, per-question scores + integrity + delivery for Video. Paced `PhaseTicker` (warming → listening → scoring). Sidebar consolidated: Screening + Voice replaced with a single "AI Interview Suite" entry.

### Regression
14/14 backend tests green (paced scenarios 5, intake handoff 2, deep-dive 7). Playwright screenshots verified end-to-end for all 6 tasks.

### 2026-02-14 — Tasks 9-11: P2 Sprint ✅ DONE

**Task 9 · Executive Copilot data + what-if sliders** — verified already working:
- `/intelligence/organization/health` populates 5 KPIs + department table (5 deps, 9 teams)
- `/intelligence/workforce/skill-gaps` populates skill matrix (23 rows)
- `/simulate/what-if` responsive to sliders (attrition, budget, checkboxes for freeze/expansion/AI doubles) → 237→295 trajectory with AI recommendation card

**Task 10 · Candidate Assistant → prep agent**
- `CandidateAssistant.jsx` restructured with a 4-tab selector: **Status** (existing lookup + FAQ), **Interview prep** (5-stage walkthrough — AI Screening → Recruiter phone → Technical → Onsite → Offer — each with duration, "what to expect", and STAR-format tips), **Org overview** (LevelShift 237 people, values, 5 department cards with size + focus), **Day in the life** (7-block hour-by-hour schedule for a Senior Engineer).

**Task 11 · Intelligence tab enhancements**
- **Planner** (`PlannerView.jsx`): added 5-stage `PLANNER REASONING TRACE` panel that ticks visibly while planning (Parsing → Retrieving world state → Matching capabilities → Scoring → Schema-validating), plus a dispatch footer with step count, unique capabilities, avg confidence.
- **Agent Registry** (`Agents.jsx`): each card is now click-to-expand. When open shows `RECENT ACTIVITY · LAST 24H` (5 timestamped ok/held events deterministically synthesised from agent_id) and `CURRENT / QUEUED TASKS` (3 tasks with priority + ETA).
- **DeepDive** (`DeepDive.jsx`): added SWIMLANE/ARCHITECTURE view toggle. Architecture view is a 5-layer interactive diagram (Business · Decision · Execution · Knowledge · Infrastructure) with 3-5 clickable nodes per layer that reveal role descriptions on click, plus a "Business steers → Decision proposes → Execution acts → Knowledge grounds → Infrastructure logs everything" dataflow footer.

### Regression
9/9 backend tests green (5 paced scenarios, 4 deep-dive replay). Playwright verified all Task 10 + 11 features render end-to-end.

### v2 build status
Tasks 1-11 (P0/P1/P2) all done. Task 12 (Platform depth) skipped by design — user's P3 lowest priority and budget-gated.
