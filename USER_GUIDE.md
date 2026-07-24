# EAROS — User Guide

**Enterprise Autonomous Recruitment Operating System**

*Version 2 · Interactive Executive Demonstration Build*

---

> **What EAROS is**
>
> EAROS is an AI operating system for talent acquisition. It separates *intelligence* (Planner, Policy Engine, Reflection) from *execution* (deterministic capabilities in a Registry), so every AI decision is auditable, replaceable, and governed by explicit policy — not buried inside an LLM prompt.

---

## Contents

**Part I · Understanding the platform**
1. [What is EAROS?](#1-what-is-earos)
2. [Core capabilities](#2-core-capabilities)
3. [Features by user persona](#3-features-by-user-persona)
4. [The architecture in one page](#4-the-architecture-in-one-page)
5. [How the AI is governed](#5-how-the-ai-is-governed)

**Part II · Using the platform**
6. [Getting in](#6-getting-in)
7. [Mission Control](#7-mission-control)
8. [Demo Scenarios](#8-demo-scenarios--the-15-minute-hero-flow)
9. [Hiring Intake → Job Architecture Agent](#9-hiring-intake--job-architecture-agent)
10. [Hiring Dashboard](#10-hiring-dashboard--drill-downs)
11. [Recruiter Copilot](#11-recruiter-copilot--the-operator-surface)
12. [Sourcing](#12-sourcing--parallel-sweep--action-plan)
13. [Resume Studio](#13-resume-studio)
14. [Outreach Studio](#14-outreach-studio)
15. [AI Interview Suite](#15-ai-interview-suite)
16. [Executive Copilot](#16-executive-copilot--what-if-simulations)
17. [Candidate Assistant](#17-candidate-assistant)
18. [Intelligence Tab](#18-intelligence-tab-planner--agents--deep-dive)
19. [World State & Governance](#19-world-state--governance)

**Part III · Playing it well**
20. [15-minute executive demo script](#20-the-recommended-15-minute-executive-demo-script)
21. [FAQ & Troubleshooting](#21-faq--troubleshooting)
22. [Glossary](#22-glossary)

---

# Part I · Understanding the platform

## 1. What is EAROS?

**EAROS** stands for *Enterprise Autonomous Recruitment Operating System*. It is an executive-class demonstration of what happens when you stop bolting AI onto a legacy ATS and instead build a **runtime** for AI recruitment work — one where every action is planned, policy-checked, executed, and reflected on.

Where a traditional ATS asks *"where is this candidate?"*, EAROS asks *"what should we do next?"* and shows the reasoning.

### Three things that make EAROS different

| | Traditional ATS + AI plugin | EAROS |
|---|---|---|
| **Intelligence** | LLM decides *and* acts in one prompt | Planner (LLM) proposes a plan; Runtime (deterministic) executes it |
| **Governance** | Audit trail is best-effort text logs | Every step emits an immutable, replayable event |
| **Risk** | AI can create offers no human signed off on | Sensitivity + confidence trigger explicit human approval gates |

### Who it is for

- **Chief People Officers** who need to prove to a board that AI recruitment is safe
- **VPs of Talent Acquisition** who need to scale a team from 3 to 30 recruiters without losing hiring bar
- **Recruiting Operations** leaders who need an auditable system-of-record for AI decisions
- **CIOs / CTOs** evaluating agentic architectures before rolling out enterprise-wide

---

## 2. Core capabilities

EAROS ships with **five architectural capabilities** that are exposed to end-users through a set of purpose-built workspaces:

### 2.1 Planner (LLM-backed)

Takes a natural-language goal and produces a schema-validated multi-step plan. Every step declares:
- The capability it calls (e.g. `cap.screen_candidate`)
- Its inputs (typed)
- The AI's confidence (0–1)
- The sensitivity level (Public / Internal / Confidential / Restricted)

The Planner is a **proposer, not a doer** — it never touches the world state directly.

### 2.2 Runtime (deterministic executor)

Executes the Planner's steps in order. For each step it:
- Retrieves the capability from the Registry
- Passes it through the Policy Engine
- Runs it and records the outcome as an immutable event
- Advances or halts based on the Governance response

### 2.3 Policy Engine (rule-based)

Evaluates every step against declared policies:
- **Fairness** — no protected-attribute inputs to ranking
- **PII** — sensitive fields never leave the workspace boundary
- **DEI** — diverse-slate enforcement on shortlists
- **Compensation** — offer bands + level guardrails
- **Sensitivity** — CONFIDENTIAL steps require human approval

Result is one of: `approved`, `blocked`, `requires_approval`.

### 2.4 Capability Registry

The catalog of every callable action:
- `cap.source_candidates` · parallel scan across 10 channels
- `cap.parse_resume` · structured extraction
- `cap.draft_outreach` · per-tone message generation
- `cap.screen_candidate` · 8-dimension rubric
- `cap.schedule_interview` · calendar coordination
- `cap.generate_offer` · comp-aligned offer letter (always CONFIDENTIAL)
- …and more

Capabilities are **versioned, swappable, and independently testable**. You can replace `cap.screen_candidate` v1 with v2 without redeploying the Planner.

### 2.5 Governance & Reflection

- **Immutable event log** — every plan, invocation, policy decision, and world-state change is appended and correlation-id-linked
- **Reflection Agent** — after every meaningful execution, writes a report of what worked, what failed, and what to adjust next time — informing future plans

---

## 3. Features by user persona

### 3.1 For **Recruiters** (`/recruiter`)

- **Autonomy toggle** — flip between *Manual*, *Semi-auto*, and *Full-auto* per requisition
- **Pipeline Intelligence strip** — live per-req stats (active count, avg fit, risk flags, offers)
- **Ops Toolbar** — email/SMS campaigns, screening blasts, resume harvester — all with recipient checklists and paced sends
- **Stage transitions** — manually advance candidates with an audit event fired on every move
- **Simulate Plan** — see the Planner's proposed sequence before it runs

### 3.2 For **Hiring Managers** (`/dashboard`, `/intake`)

- **Clickable KPI dashboard** — every tile drills into its underlying records
- **Job Architecture Agent** — paste a brief in English, get a JD + sourcing plan + a matched requisition in seconds
- **What-if hiring simulations** — see how a delay or headcount change moves the trajectory

### 3.3 For **Executives** (`/executive`)

- **Workforce simulation** — attrition, budget, expansion, and AI-headcount levers with per-month trajectory
- **AI Recommendation card** with reasoning, evidence, tradeoffs, and residual risks
- **Skill demand + department health** — where the org is bottlenecked and by how much

### 3.4 For **Candidates** (`/candidate`)

- **Status lookup** — where they are in the process and what's next
- **Interview prep** — 5-stage walkthrough with STAR-format tips
- **Org overview** — company snapshot, values, departments
- **Day in the life** — realistic hour-by-hour schedule

### 3.5 For **Admins / Auditors** (`/governance`, `/agents`, `/deep-dive`)

- **Immutable audit log** with correlation-id search
- **Agent registry** — health, latency, cost, recent activity per agent
- **Deep-Dive replay** — swimlane view of every agent-to-agent event in an execution
- **Layered architecture diagram** — click any node for its role

---

## 4. The architecture in one page

EAROS is organised in **five layers**. Every feature you see in the UI is one of these layers rendered in a different way.

```
┌───────────────────────────────────────────────────────────────┐
│  BUSINESS LAYER · the "why"                                    │
│  Policy Manager · Objectives · Governance                      │
├───────────────────────────────────────────────────────────────┤
│  DECISION LAYER · the "what"                                   │
│  Planner · Policy Engine · Strategy Agent · Reflection         │
├───────────────────────────────────────────────────────────────┤
│  EXECUTION LAYER · the "how"                                   │
│  Runtime · Capability Registry · Sourcing · Outreach · Screen  │
├───────────────────────────────────────────────────────────────┤
│  KNOWLEDGE LAYER · grounded facts                              │
│  World State · Episodic Memory · Skill Graph                   │
├───────────────────────────────────────────────────────────────┤
│  INFRASTRUCTURE LAYER · plumbing                               │
│  Event Bus · Auth (Google OAuth) · Observability · MongoDB     │
└───────────────────────────────────────────────────────────────┘
```

**Dataflow:** *Business steers* → *Decision proposes* → *Execution acts* → *Knowledge grounds* → *Infrastructure logs everything.*

You can see this diagram live at `/deep-dive` → click **ARCHITECTURE** in the top-right.

---

## 5. How the AI is governed

Governance in EAROS is not a report — it is a runtime.

### Every AI action generates an event

Events are appended to an immutable log with a correlation id that links them into an *execution* you can replay. Event types include:

- `PLAN_CREATED` · Planner proposed a plan
- `POLICY_EVALUATED` · Policy Engine allowed or blocked a step
- `CAPABILITY_INVOKED` · Runtime called a capability
- `APPROVAL_REQUESTED` · a CONFIDENTIAL step needs a human
- `APPROVAL_DECIDED` · a human approved / rejected
- `CANDIDATE_STAGE_CHANGED` · pipeline moved
- `REFLECTION_RECORDED` · what was learned

### Human approval gates are real

Steps marked `sensitivity=CONFIDENTIAL` (offers, comp negotiations, terminations, PII exports) always require an explicit human click. There is no auto-approve. If nobody clicks within 10 minutes, the step is **cancelled** — not silently released.

### Every recommendation is explainable

The Planner outputs its full reasoning chain: goal parsing → world-state retrieval → capability matching → step scoring. You can see this live at `/planner`.

---

# Part II · Using the platform

## 6. Getting in

**Preview (dev):** `https://hiring-runtime.preview.emergentagent.com`
**Production:** `https://hiring-runtime.emergent.host`

Two ways to sign in:

| Method | When to use |
|---|---|
| **Continue with Google** (Emergent-managed OAuth) | Real users on production. Role inferred from email. |
| **Demo buttons** (Recruiter · Hiring Manager · Executive · Candidate · Admin) | Instant, no email. Ideal for live demos. |

> **Tip** · The Executive demo unlocks the workforce-simulation What-If sliders. The Recruiter demo unlocks the operational studios. Start with **Recruiter** for most demos.

---

## 7. Mission Control

**Route:** `/mission`

The persistent top-nav shows the six primary surfaces. The main page shows:

- Top P0 requisitions and aging offers
- A live event ticker (last N events through the runtime)
- Quick-start scenario launchers

Every demo starts here — this is your context-setting screen.

---

## 8. Demo Scenarios — the 15-minute hero flow

**Route:** `/scenarios`

The **centerpiece** of any executive walkthrough. Each scenario runs the complete lifecycle — Intake → JD → Sourcing → Screening → Outreach → Interview → **Offer (held for human approval)** → Reflection — with pacing so viewers can watch each agent think.

### How to run one

1. Pick a scenario card (e.g. *Salesforce Architect · Austin*)
2. Click **RUN SCENARIO**
3. Watch the live panel:
   - Current-step banner naming the active agent
   - Progress bar with step counter (*Step 6 / 14 · 43%*)
   - Per-step outputs as they complete
4. At step 13 the scenario **pauses** with an amber card:

   > **HUMAN APPROVAL REQUIRED**
   > *Offer for Shreya Chatterjee*
   > *Policy requires human approval for CONFIDENTIAL offers above L2. AI confidence 0.86.*
   > **SCENARIO CANCELS IN** `9:47`
   > `[ APPROVE OFFER ]  [ REJECT ]`

5. Click **APPROVE OFFER** to release the gate — Reflection runs and the scenario completes
6. Use **OPEN REPLAY →** to see the swimlane replay, or **AUDIT →** to see every recorded event

> **What this proves** · Policy actually gates AI actions. The pause is real — you can wait 10 minutes; nothing auto-approves.

---

## 9. Hiring Intake → Job Architecture Agent

**Route:** `/intake`

Paste a plain-English brief (or use a pre-loaded example). The **Job Architecture Agent** flow lights up in four steps:

1. **Requirements Agent** — extract must-haves, seniority, location, comp, urgency
2. **Job Architecture Agent** — generate a calibrated JD with responsibilities + comp band
3. **Sourcing Strategy Agent** — 3-wave sourcing plan with Boolean search string
4. **Recruiter Handoff** — match to the closest existing requisition

Click **OPEN IN RECRUITER COPILOT →** and the matched req is pre-selected.

> **Resilience** · If the LLM stalls, the agent retries 3× on the frontend and 2× on the backend, then falls back to a deterministic parser. Users never see a raw gateway error.

---

## 10. Hiring Dashboard — drill-downs

**Route:** `/dashboard`

Six KPI tiles — each is **clickable** and opens a right-side drill drawer:

| KPI | Drill-down shows |
|---|---|
| Open reqs | Active requisitions with priority + location + days-open |
| In pipeline | Every non-terminal candidate |
| Offers active | Everyone in offer stage |
| Hired YTD | Everyone marked hired |
| Avg time-to-fill | Reqs sorted worst-first |
| P0 roles | Board-level critical priorities |

Every drill-down row deep-links into the Recruiter Copilot with the correct requisition pre-selected.

---

## 11. Recruiter Copilot — the operator surface

**Route:** `/recruiter` (or `/recruiter?job=<job_id>` to preselect)

### Autonomy toggle

Flip between three modes at any time:

- **Manual** — AI recommends. Every action needs a click.
- **Semi-auto** — AI acts on low-risk steps; humans approve offers, comp, comms.
- **Full-auto** — AI runs the full lifecycle within policy. Humans audit after.

### Pipeline Intel strip

Live per-req metrics: Active · Avg fit % · Risk flags · Offers · Autonomy mode.

### Ops toolbar

| Tool | What it does |
|---|---|
| **Email campaign** | Multi-select recipients → subject + body with `{{first_name}}` / `{{role}}` templating → paced send with audit trail |
| **SMS campaign** | Short-form outreach with the same recipient checklist |
| **Screening blast** | Fires async AI screening to N candidates in parallel |
| **Resume harvester** | Drop `.pdf/.docx` — auto-parse, dedupe against ATS |

### Candidate detail

Selecting a candidate shows their profile, fit score, skill chips, and a **stage transition** dropdown. Every transition emits an immutable `CANDIDATE_STAGE_CHANGED` audit event.

### Simulate plan

Click **SIMULATE PLAN** to see the Planner build a multi-step plan for the selected candidate.

---

## 12. Sourcing — parallel sweep + action plan

**Route:** `/sourcing`

1. Pick a requisition
2. Click **RUN SWEEP** — 10 channels scan in parallel: GitHub · LinkedIn · Dice · Internal ATS · Referrals · Naukri · Hired · Stack Overflow · AngelList · Gem. Each returns match counts + quality scores.
3. Summary cards: Total matches · Unique candidates · Duplicates removed · Weighted quality
4. **Recommended Action Plan** appears with 4 executable next steps:
   - `cap.draft_outreach` — Contact top 25 (→ Outreach Studio)
   - `cap.screen_candidate` — AI screen top 10 (→ Screening)
   - `cap.retarget` — Retarget silver-medalists from the top source
   - `cap.schedule_interview` — Schedule 5 with the hiring manager

Each button turns green after you trigger it.

---

## 13. Resume Studio

**Route:** `/resume`

Paste a resume + pick a target job. The parser extracts skills, experience, comp expectations, and right-to-work signals. Then pick a **format**:

- **One-page summary** — compact recruiter-facing card
- **Client submission** — full anonymised package with skills matrix (verified vs role), differentiators, comp/logistics footer, PII-redacted watermark

Both formats have download buttons.

---

## 14. Outreach Studio

**Route:** `/outreach`

**Left column** — searchable multi-select **recipient list**. Filter by name / title / location.

**Right column** — pick a template-source candidate → click **GENERATE PACK**. The AI produces:

- **3 email variants** — Warm / Neutral / Formal — each with response probability, editable subject + body, and a **SEND TO N** button
- **LinkedIn InMail · SMS · WhatsApp · Voice Script** — each with a send button

Sending triggers a **paced send** with a live "Sending…" → "Sent · tracked in Governance" banner.

---

## 15. AI Interview Suite

**Route:** `/interview`

One suite, **four modes**:

| Mode | Use case | Report contains |
|---|---|---|
| **AI Screening** | 5-minute async structured screen | 8-dimension rubric with scores, weights, notes; composite + band |
| **AI Voice** | Live 12-minute conversational phone screen | Transcript signals (Technical Depth, Structured Thinking, Motivation, Culture, Red Flags), followups |
| **AI Copilot** | Live human interview with real-time AI assist | Live per-area scoring, AI-suggested followups, AI flags, scorecard draft |
| **Autonomous Video** | Fully AI-driven async video | Per-question scores, integrity (face-match, screen capture), delivery (confidence, WPM, filler words) |

Pick a mode → candidate → optional context → action button. A `PhaseTicker` (Warming → Listening → Scoring) plays before the report renders.

---

## 16. Executive Copilot — What-If simulations

**Route:** `/executive`

Five KPI cards on top (headcount, attrition YTD, open reqs, offers active, WFP alignment).

### What-If sliders

- **Attrition %** · dial current 12% up to 35%
- **Budget delta %** · ± vs baseline
- **Hiring freeze** · checkbox
- **Bangalore expansion** · checkbox
- **AI Engineering doubles** · checkbox
- **Horizon** · 6 / 12 / 24 months

Click **RUN SIMULATION** — you get a starting → ending headcount, a per-month trajectory chart, and an AI Recommendation card with **reasoning · evidence · tradeoffs · residual risks**.

### Below

- **Department health** — capacity, hiring velocity, at-risk teams
- **Skill demand** — top skill gaps by scarcity × business criticality

---

## 17. Candidate Assistant

**Route:** `/candidate`

The candidate-safe view. Four tabs:

- **Status** — enter a candidate id → stage + next step
- **Interview prep** — 5-stage walkthrough with STAR tips
- **Org overview** — company snapshot, values, departments
- **Day in the life** — hour-by-hour schedule

No confidential data ever crosses this boundary.

---

## 18. Intelligence Tab (Planner · Agents · Deep-Dive)

### Planner — `/planner`

Type a goal + optional JSON context → **GENERATE**. The **Planner Reasoning Trace** shows 5 phases ticking through:

1. Parsing goal
2. Retrieving world state
3. Matching capabilities
4. Scoring & ordering steps
5. Schema-validating plan

Dispatch footer shows step count · unique capabilities · avg confidence.

### Agents — `/agents`

Each agent has a card with: name · version · health · 24h runs · latency · cost · inputs · outputs · capability dependencies.

Click any card to expand:
- **Recent activity · last 24h** — 5 timestamped events (ok / held)
- **Current / queued tasks** — 3 tasks with priority + ETA

### Deep-Dive — `/deep-dive`

Two views (toggle in the top right):

- **SWIMLANE** — pick a past execution → replay every agent-to-agent event with real payloads, confidence, sensitivity, and policy hits
- **ARCHITECTURE** — the 5-layer interactive diagram. Click any node for its role.

---

## 19. World State & Governance

### World State — `/world`

Seven sub-tabs, all switch live:

- **Organization** — LevelShift snapshot
- **Departments** — 5 departments with size + focus
- **Teams** — 9 teams with charter + capacity
- **Jobs** — every req with priority + location + status
- **Candidates** — all 152 candidates with stage + fit score
- **Offers** — offers in flight
- **Skills** — the skill graph with supply/demand

### Governance — `/governance`

The immutable audit log. Filter by actor, subject, event type, or time window. Every row is signed with a correlation id — click to jump to the swimlane replay.

---

# Part III · Playing it well

## 20. The recommended 15-minute executive demo script

Copy-paste this. Timing is deliberate.

| Time | Screen | What to show |
|---|---|---|
| 0:00 | Landing | Click **Recruiter** demo — land on Mission Control |
| 0:30 | `/scenarios` | Run *Salesforce Architect · Austin*. Narrate: "Watch each agent think — it's paced so you see the reasoning." |
| 3:00 | `/scenarios` | The scenario hits the **Human Approval Gate** — pause here. "Policy requires a human. AI doesn't cross this line." Click **APPROVE**. |
| 4:00 | `/scenarios` → **OPEN REPLAY** | Show the swimlane replay. "Every event is immutable." |
| 5:30 | `/intake` | Paste a fresh brief. "Job Architecture Agent — 4 sub-agents, 6 seconds." Click handoff. |
| 7:00 | `/recruiter?job=…` | Flip to **Full-auto**. Show the ops toolbar. Launch an Email campaign to 3 candidates. |
| 9:00 | `/executive` | Slide attrition to 22%. "That's a $4M scenario." Click **RUN SIMULATION**. |
| 11:00 | `/deep-dive` → **ARCHITECTURE** | Show the 5-layer diagram. "Intelligence separated from execution." |
| 13:00 | `/governance` | Filter to `POLICY_EVALUATED`. "Every AI decision is auditable." |
| 14:30 | Q&A | |

### Talking points that land

- *"The AI never touches the world state directly. It proposes; the Runtime disposes."*
- *"CONFIDENTIAL is not a label — it's a runtime gate."*
- *"Reflection means the system gets better between demos, not just between releases."*
- *"Every capability is versioned. We can swap the screener from v1 to v2 without redeploying the Planner."*

---

## 21. FAQ & Troubleshooting

**Q: The scenario reached the approval gate but nothing happens when I click APPROVE.**
Refresh and re-run. Rarely, the polling loop can lose the execution id after a very long idle period. Server state is preserved for 24 hours.

**Q: The intake flow shows a "TRY AGAIN" button.**
The upstream LLM was briefly unreachable. The backend has already fallen back to a deterministic parser that produces a credible intake. Click **TRY AGAIN** or the **Analyze** button — you will get a valid result within ~50 seconds worst case.

**Q: I'm on the executive demo but I don't see the What-If sliders.**
Log out (top-right) and click the **Executive** demo button on the landing page — not Recruiter.

**Q: How do I reset the demo data?**
The seed re-runs on every backend restart. All 152 candidates, 12 requisitions, and 5 scenarios are idempotent. Contact Emergent Support to restart the pod.

**Q: Where do I download the report / signed offer?**
Every generated artifact has a download affordance in the studio that produced it (Resume Studio, Outreach Studio, Interview Suite reports). Storage is Governance-tracked — nothing leaves the system unlogged.

**Q: Can I try Google OAuth instead of the demo buttons?**
Yes — click **Continue with Google** on the landing page. Your role is inferred from the email domain.

**Q: Preview vs Production — where should I demo?**
Demo from **Production** (`https://hiring-runtime.emergent.host`) — it's the version your buyers will use. Preview is for testing changes before deploy.

---

## 22. Glossary

| Term | Meaning |
|---|---|
| **Capability** | A callable, versioned action (e.g. `cap.screen_candidate`) registered in the Capability Registry |
| **Confidence** | The Planner's self-assessed likelihood the step will succeed (0–1) |
| **Correlation ID** | A single id shared by every event in one logical execution |
| **Execution** | A run of a plan — one goal, N steps, one correlation id |
| **Governance** | The immutable audit log + approval workflow |
| **Planner** | The LLM-backed proposer; produces schema-validated plans |
| **Policy Engine** | The rule-based evaluator; approves, blocks, or requires-approval |
| **Reflection** | Post-execution report: what worked, what failed, what to change |
| **Runtime** | The deterministic executor of Planner steps |
| **Sensitivity** | One of Public / Internal / Confidential / Restricted — drives approval requirements |
| **World State** | The grounded facts (jobs, candidates, offers, skills) — the ATS surface |

---

## Support

- **Preview & bugs** · your Emergent success manager
- **Production incidents** · Emergent Support
- **Feature requests / feedback** · commits with `feat:` prefix are tracked

---

*EAROS · Planner → Runtime → Policy Engine → Capability Registry → Governance. Every intelligence decision is separated from execution — auditable, replaceable, and human-gated where it matters.*
