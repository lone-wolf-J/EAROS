# EAROS — User Guide

**Enterprise Autonomous Recruitment Operating System · v2**

A live, interactive demonstration of an AI operating system for talent acquisition. This guide walks you through every screen, what it proves, and the exact click-path to run a compelling executive demo.

---

## Contents

1. [Getting in](#1-getting-in)
2. [Mission Control](#2-mission-control-your-home-base)
3. [Demo Scenarios](#3-demo-scenarios-the-15-minute-hero-flow)
4. [Hiring Intake](#4-hiring-intake--job-architecture-agent)
5. [Hiring Dashboard](#5-hiring-dashboard--drill-downs)
6. [Recruiter Copilot](#6-recruiter-copilot--the-operator-surface)
7. [Sourcing](#7-sourcing--parallel-sweep--action-plan)
8. [Resume Studio](#8-resume-studio)
9. [Outreach Studio](#9-outreach-studio)
10. [AI Interview Suite](#10-ai-interview-suite)
11. [Executive Copilot](#11-executive-copilot--what-if-simulations)
12. [Candidate Assistant](#12-candidate-assistant)
13. [Intelligence Tab](#13-intelligence-tab-planner--agents--deep-dive)
14. [World State & Governance](#14-world-state--governance)
15. [The Recommended Demo Script](#15-the-recommended-15-minute-executive-demo-script)
16. [FAQ](#16-faq--troubleshooting)

---

## 1. Getting in

**Preview (dev):** `https://hiring-runtime.preview.emergentagent.com`
**Production:** `https://hiring-runtime.emergent.host`

There are two ways to sign in:

| Method | When to use |
|---|---|
| **Continue with Google** (Emergent-managed OAuth) | Real users on production. Roles inferred from email. |
| **Demo buttons** (Recruiter · Hiring Manager · Executive · Candidate · Admin) | Instant, no email. Ideal for live demos. |

Click any demo button on the landing page — you land on **Mission Control** immediately with all the right permissions for that persona.

> **Tip:** The **Executive** demo unlocks the workforce-simulation What-If sliders. The **Recruiter** demo unlocks the operational studios. Start with Recruiter for most demos.

---

## 2. Mission Control (your home base)

**Route:** `/mission`

The persistent top-nav shows the six primary surfaces. The main page shows:

- **Today's board** — top P0 reqs, aging offers, at-risk pipelines
- **Live event ticker** — the last N events that flowed through the runtime
- **Quick-start scenarios** — one-click launchers

**Use it for:** setting context before you drill anywhere. Every demo starts here.

---

## 3. Demo Scenarios — the 15-minute hero flow

**Route:** `/scenarios`

This is the **centerpiece** of any executive walkthrough. Each scenario runs the complete lifecycle — Intake → JD → Sourcing → Screening → Outreach → Interview → **Offer (held for human approval)** → Reflection — with pacing so executives can watch each agent think.

### How to run one

1. Pick a scenario card (e.g. *Salesforce Architect · Austin*).
2. Click **RUN SCENARIO**.
3. Watch the live panel:
   - Current-step banner naming the active agent (e.g. `Sourcing Agent · Scanning GitHub, LinkedIn, Dice…`)
   - Progress bar with step counter (e.g. *Step 6 / 14 · 43%*)
   - Per-step outputs as they complete
4. At step 13, the scenario **pauses** with a bold amber card:

   > **HUMAN APPROVAL REQUIRED**
   > *Offer for Shreya Chatterjee*
   > *Policy requires human approval for CONFIDENTIAL offers above L2. AI confidence 0.86.*
   > **SCENARIO CANCELS IN** `9:47`
   > `[ APPROVE OFFER ]  [ REJECT ]`

5. Click **APPROVE OFFER** to release the gate — the Reflection step runs and the scenario completes.
6. On completion, use **OPEN REPLAY →** to jump straight into the swimlane replay of the same execution, or **AUDIT →** to see every immutable event recorded.

> **What this proves:** Policy actually gates AI actions. The pause is real — you can wait 10 minutes; nothing auto-approves.

---

## 4. Hiring Intake → Job Architecture Agent

**Route:** `/intake`

Executives paste a plain-English brief (or use one of the pre-loaded examples). The **Job Architecture Agent** flow lights up:

1. **Requirements Agent** — extracting must-haves, seniority, location, compensation, urgency
2. **Job Architecture Agent** — generating a calibrated JD with responsibilities and comp band
3. **Sourcing Strategy Agent** — 3-wave sourcing plan with Boolean search string
4. **Recruiter Handoff** — matches to the closest existing requisition

When it's done, click **OPEN IN RECRUITER COPILOT →** and the matched req is pre-selected. The multi-wave plan (P0/P1/P2 channels + target candidate counts + estimated reach + sweep minutes) is right on the same page.

> **Resilience:** If the LLM stalls, the agent retries 3× on the frontend and 2× on the backend, then falls back to a deterministic parser. You will never see a raw gateway error.

---

## 5. Hiring Dashboard — drill-downs

**Route:** `/dashboard`

Six KPI tiles — each is **clickable**:

| KPI | Drill-down shows |
|---|---|
| Open reqs | All active requisitions with priority + location + days-open |
| In pipeline | Every non-terminal candidate |
| Offers active | Everyone in offer stage |
| Hired YTD | Everyone marked hired |
| Avg time-to-fill | Reqs sorted worst-first |
| P0 roles | Board-level critical priorities |

Every drill-down row links directly to the Recruiter Copilot with the correct requisition pre-selected.

---

## 6. Recruiter Copilot — the operator surface

**Route:** `/recruiter` (or `/recruiter?job=<job_id>` to preselect)

### Header

- **Autonomy toggle:** *Manual · Semi-auto · Full-auto*
  - **Manual** — AI recommends. Every action needs a click.
  - **Semi-auto** — AI acts on low-risk steps; humans approve offers, comp, comms.
  - **Full-auto** — AI runs the full lifecycle within policy. Humans audit after.

### Pipeline Intel strip

Live per-req metrics: Active count · Avg fit % · Risk flags · Offers · Autonomy mode.

### Ops toolbar (4 tools)

| Tool | What it does |
|---|---|
| **Email campaign** | Multi-select recipients → subject + body with `{{first_name}}` / `{{role}}` / `{{signal}}` templating → paced send with governance audit trail |
| **SMS campaign** | Short-form outreach with the same recipient checklist |
| **Screening blast** | Fires an async AI screening to N candidates in parallel |
| **Resume harvester** | Drop `.pdf/.docx` — auto-parse, structured extraction, dedupe against ATS |

### Candidate detail card

Selecting a candidate shows their profile, fit score, skill chips, and a **stage transition** dropdown (Sourced → Screening → Phone screen → Technical → Onsite → Offer → Hired / Rejected / Withdrawn). Every transition emits an immutable `CANDIDATE_STAGE_CHANGED` audit event.

### Simulate plan

Click **SIMULATE PLAN** to see the Planner build a multi-step plan for the selected candidate. Confidence, sensitivity, and policy hits are all visible before you execute.

---

## 7. Sourcing — parallel sweep + action plan

**Route:** `/sourcing`

1. Pick a requisition.
2. Click **RUN SWEEP** — 10 channels scan in parallel (GitHub, LinkedIn, Dice, Internal ATS, Referrals, Naukri, Hired, Stack Overflow, AngelList, Gem). Each returns match counts + quality scores independently.
3. Summary cards appear: Total matches · Unique candidates · Duplicates removed · Weighted quality.
4. A **Recommended Action Plan** appears with 4 executable next steps:
   - `cap.draft_outreach` — Contact top 25 (opens Outreach Studio)
   - `cap.screen_candidate` — AI screen top 10 (opens Screening)
   - `cap.retarget` — Retarget silver-medalists from the top source
   - `cap.schedule_interview` — Schedule 5 with the hiring manager

Each button turns green after you trigger it.

---

## 8. Resume Studio

**Route:** `/resume`

Paste a resume + pick the target job. The parser extracts skills, experience, comp expectations, right-to-work signal. Then choose a **format**:

- **One-page summary** — compact recruiter-facing card
- **Client submission** — full anonymised package with a header, skills matrix (verified vs role), differentiators, comp/logistics footer, and a PII-redacted watermark

Both formats have download buttons.

---

## 9. Outreach Studio

**Route:** `/outreach`

**Left column** — a searchable, multi-select **recipient list**. Filter by name / title / location, tick as many as you want.

**Right column** — pick a template-source candidate → click **GENERATE PACK**. The AI produces:

- **3 email variants** — Warm, Neutral, Formal — each with response probability, editable subject + body, and a **SEND TO N** button
- **LinkedIn InMail, SMS, WhatsApp, Voice Script** — each with a send button

Clicking send triggers a **paced send** — "Sending Email · warm to 12 candidates…" → "Email · warm sent to 12 candidates · tracked in Governance".

---

## 10. AI Interview Suite

**Route:** `/interview`

One suite, **four modes** — pick the modality that fits the moment:

| Mode | Use case | Report contains |
|---|---|---|
| **AI Screening** | 5-minute async structured screen | 8-dimension rubric with scores, weights, notes; composite score with band |
| **AI Voice** | Live 12-minute conversational phone screen | Transcript signal (Technical Depth, Structured Thinking, Motivation, Culture, Red Flags), recommended followups |
| **AI Copilot** | Live human interview with real-time AI assist | Live per-area scoring, AI-suggested followups, AI flags, scorecard draft |
| **Autonomous Video** | Fully AI-driven async video | Per-question scores, integrity signals (face-match, screen capture, latency pattern), delivery signals (confidence, WPM, filler words) |

Pick a mode → pick a candidate → optional context → click the action button. A `PhaseTicker` (Warming → Listening → Scoring) plays before the report renders.

---

## 11. Executive Copilot — What-If simulations

**Route:** `/executive`

Five KPI cards on top (headcount, attrition YTD, open reqs, offers active, WFP alignment).

### What-If sliders

- **Attrition %** — dial current 12% up to 35% and watch the trajectory
- **Budget delta %** — plus/minus versus baseline
- **Hiring freeze** — checkbox
- **Bangalore expansion** — checkbox
- **AI Engineering doubles** — checkbox
- **Horizon** — 6, 12, or 24 months

Click **RUN SIMULATION** — you get a starting → ending headcount line, a per-month trajectory chart, and an AI Recommendation card with reasoning, evidence, tradeoffs, and residual risks.

### Below

- **Department health** — per-department capacity, hiring velocity, at-risk teams
- **Skill demand** — top skill gaps ranked by scarcity + business criticality

---

## 12. Candidate Assistant

**Route:** `/candidate`

The candidate-safe view — nothing confidential ever crosses this boundary. Four tabs:

- **Status** — enter a candidate id and see stage + next step (great for demoing to candidates directly)
- **Interview prep** — 5-stage walkthrough with durations, "what to expect" and STAR-format tips
- **Org overview** — LevelShift snapshot, values, department cards
- **Day in the life** — hour-by-hour schedule for a Senior Engineer

---

## 13. Intelligence Tab (Planner · Agents · Deep-Dive)

### Planner — `/planner`

Type a goal + optional JSON context, hit **GENERATE**. The **Planner Reasoning Trace** shows 5 phases ticking through:

1. Parsing goal
2. Retrieving world state
3. Matching capabilities
4. Scoring & ordering steps
5. Schema-validating plan

The dispatch footer shows step count, unique capabilities, and average confidence.

### Agents (Registry) — `/agents`

Every agent has a card with: name · version · health · 24h runs · latency · cost · inputs · outputs · capability dependencies.

Click any card to **expand**:

- **Recent activity · last 24h** — 5 timestamped events (ok / held)
- **Current / queued tasks** — 3 tasks with priority + ETA

### Deep-Dive — `/deep-dive`

Two views (toggle in the top right):

- **SWIMLANE** — pick a past execution → replay every agent-to-agent event in order, with real payloads, confidence, sensitivity, and policy hits
- **ARCHITECTURE** — a 5-layer interactive diagram (Business · Decision · Execution · Knowledge · Infrastructure). Click any node for its role.

---

## 14. World State & Governance

### World State — `/world`

Six sub-tabs (all switch live):

- **Organization** — LevelShift snapshot
- **Departments** — 5 departments with size + focus
- **Teams** — 9 teams with charter + capacity
- **Jobs** — every req with priority + location + status
- **Candidates** — all 152 candidates with stage + fit score
- **Offers** — offers in-flight
- **Skills** — the skill graph with supply/demand

### Governance — `/governance`

The immutable audit log. Every event that has ever flowed through the system: `PLAN_CREATED`, `CAPABILITY_INVOKED`, `POLICY_EVALUATED`, `CANDIDATE_STAGE_CHANGED`, `APPROVAL_REQUESTED`, `APPROVAL_DECIDED`, and 15 more. Filter by actor, subject, event type, or time window. Every row is signed with a correlation id — click to jump to the swimlane replay.

---

## 15. The recommended 15-minute executive demo script

Copy-paste this. Timing is deliberate.

| Time | Screen | What to show |
|---|---|---|
| 0:00 | Landing | Click **Recruiter** demo — land on Mission Control |
| 0:30 | `/scenarios` | Run *Salesforce Architect · Austin*. Narrate: "Watch the AI think — it's paced so you can see each agent." |
| 3:00 | `/scenarios` | The scenario hits the **Human Approval Gate** — pause here. "Policy requires a human. AI doesn't cross this line." Click **APPROVE**. |
| 4:00 | `/scenarios` → **OPEN REPLAY** | Show the swimlane replay. "Every event is immutable." |
| 5:30 | `/intake` | Paste a fresh brief. "This is the Job Architecture Agent — 4 sub-agents in 6 seconds." Click handoff. |
| 7:00 | `/recruiter?job=…` | Flip to **Full-auto**. Show the ops toolbar. Launch an Email campaign to 3 candidates. |
| 9:00 | `/executive` | Slide attrition to 22%. "That's a $4M scenario." Click **RUN SIMULATION**. |
| 11:00 | `/deep-dive` → **ARCHITECTURE** | Show the 5-layer diagram. "Intelligence separated from execution. Every layer testable, replaceable." |
| 13:00 | `/governance` | Filter to `POLICY_EVALUATED`. "Every AI decision is auditable." |
| 14:30 | Q&A |

---

## 16. FAQ · Troubleshooting

**Q: The scenario reached the approval gate but nothing happens when I click APPROVE.**
Refresh the page and re-run. Rarely, the polling loop can lose the execution id after a very long idle period. All state is preserved server-side for 24 hours.

**Q: The intake flow shows a "TRY AGAIN" button.**
The upstream LLM was briefly unreachable. Click **TRY AGAIN**. If it still fails, the backend falls back to a deterministic parser that still produces a credible intake — click **Analyze** again.

**Q: I'm on the executive demo but I don't see the What-If sliders.**
Log out (top-right) and click the **Executive** demo button on the landing page — not Recruiter.

**Q: How do I reset the demo data?**
The seed re-runs on every backend restart. All 152 candidates, 12 reqs, and 5 scenarios are idempotent. Contact Emergent Support to restart the pod.

**Q: Where do I download the report / signed offer?**
Every generated artifact has a download affordance in the studio that produced it (Resume Studio, Outreach Studio, Interview Suite reports). Storage is Governance-tracked — nothing leaves the system unlogged.

**Q: Can I try Google OAuth instead of the demo buttons?**
Yes — click **Continue with Google** on the landing page. Your role is inferred from the email domain. `@levelshift.ai` addresses map to internal roles; anything else defaults to Candidate.

---

## Support

- **Preview & bugs:** contact your Emergent success manager
- **Production incidents:** Emergent Support
- **Feature requests / feedback:** any commit sent to the repo with the `feat:` prefix is tracked

---

*Built on the EAROS architecture · Planner · Runtime · Policy Engine · Capability Registry · Governance. Every intelligence decision is separated from execution — auditable, replaceable, and human-gated where it matters.*
