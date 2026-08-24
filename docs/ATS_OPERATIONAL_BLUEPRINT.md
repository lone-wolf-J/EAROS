# EAROS Operational ATS Blueprint

## Product operating model

EAROS will treat a **requisition** as the approved operating container for hiring, not merely a job description. It owns the hiring plan, team, pipeline, application requirements, evaluation plan, publication state, and approval context. A **candidate** is a tenant-scoped person record; an **application** is the candidate’s immutable, requisition-specific lifecycle. This separation supports one person applying to multiple roles without losing stage history, source attribution, or decision evidence.

> Final hire and rejection outcomes remain governed actions. A recruiter can make operational progress, but EAROS must independently approve a final decision whenever policy requires it.

## Requisition workspace

| Section | Required operating fields | Control boundary |
|---|---|---|
| Identity and ownership | Requisition code, title, department, team, cost center, recruiter, coordinator, hiring manager, hiring team | All people must be active members of the same organization. |
| Workforce plan | Headcount, replacement/new headcount, employment type, seniority, work arrangement, primary location, countries, target start and close dates, business justification | Creation and changes are auditable; approval state controls publication. |
| Compensation | Currency, minimum/maximum range, pay period, bonus/equity guidance, visibility policy | Internal planning data; no candidate offer delivery occurs here. |
| Job definition | Public and internal description, responsibilities, required/preferred skills, education/work authorization, EEO/privacy language, attachments | Public content is independently controlled by internal publication state. |
| Process design | Pipeline template, stage SLAs, stage owners, application questions, source/referral settings, interview plan, scorecard template, offer approval route | The selected configuration is snapshotted into applications to preserve provenance. |
| Publication | Career site, internal jobs, referral intake, provider targets, localized versions, publication history | Provider targets remain draft-only until an approved connector exists. |

Requisition detail edits are auditable planning operations. EAROS validates hiring-manager, recruiter, coordinator, and offer-approver user references against the active tenant and role constraints before saving. Publication state, candidate-facing questions, and application state are deliberately excluded from this editor. A pipeline can be changed only before the requisition has applications, preserving lifecycle provenance.

## Candidate and application operations

The recruiter workbench will provide separate but connected views: **My work**, **Requisitions**, **Pipeline**, **Candidate CRM**, **Interviews**, **Offers**, and **Reporting**. Pipeline controls will support stage movement, filter/search, bulk review, disqualification, withdrawal, restore, assignment, source review, and timeline access. Every move will write a stage-history record with acting user, source stage, target stage, timestamp, reason, and supporting notes. Terminal outcomes preserve the independent decision gate.

> **Terminal correction rule.** An approved `Hired` or `Rejected` outcome cannot be reversed through ordinary stage movement. EAROS records a separate tenant-scoped reactivation request with the target active stage and evidence-based rationale. Its requester cannot decide it. Only an independent governance grant reactivates the application, preserves the original hiring decision, appends the approval and correction identifiers to stage history, and emits dedicated request/effective/denied events and activity records.

> **Configurable stage-control rule.** When a tenant marks a current pipeline stage as feedback-required, an application cannot leave that stage until a submitted interview-feedback record is linked to the application and that stage. Bulk stage movement performs the same validation for every selected record before any mutation, excludes terminal applications, records a shared bulk-operation correlation identifier in each history/activity record, and emits both per-application and aggregate governance events.

> **Pipeline reporting rule.** The recruiter workbench aggregates current-stage dwell time from the tenant’s durable application stage history. It reports both the record count and the count with a trustworthy recorded stage-entry time; records created before durable history existed deliberately show no average rather than a fabricated duration.

## Interview and decision operations

Interview plans associate stages with an interview type, duration, timezone, interviewer roles, interview kit, focus competencies, and scorecard. Recruiters can coordinate records and reminders, while a calendar/video provider remains configured-but-inactive until supplied. Feedback is independently authored, has completion visibility, and drives a debrief packet. Offer packages remain internal drafts with version history, approval route, compensation components, and candidate-response record; an accepted handoff is limited to downstream routing metadata.

## Delivery increments

| Increment | Scope | Completion evidence |
|---|---|---|
| 1 | Complete requisition model and recruiter form | Model/API/frontend contracts, role and tenant checks. |
| 2 | Operational pipeline board and application stage actions | Stage transition, disposition/restore, audit, and browser contracts. |
| 3 | Candidate workbench and interview plan expansion | Candidate/application context, scorecard and interview-plan contracts. |
| 4 | Offer, reporting, and configured-but-inactive integrations | Approval, reporting, no-provider, and journey contracts. |

## Non-negotiable constraints

No UI control may imply an email, SMS, calendar, job-board, assessment, background-check, e-signature, or SSO provider is connected. Every cross-tenant read and mutation is denied. Human approval remains mandatory for governed destructive, distribution, and final hiring actions. AI recommendations are explainable, non-final, policy checked, and audited.
