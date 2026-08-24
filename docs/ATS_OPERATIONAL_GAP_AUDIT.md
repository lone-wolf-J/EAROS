# EAROS Operational ATS Gap Audit

## Finding

The current EAROS source contains durable ATS entities and governed controls, but its primary recruiter screen still exposes a **minimal operator experience**. The current requisition modal accepts only title, headcount, location, pipeline, basic hiring-plan text, and target dates. The application workspace lists candidates and current stages but does not expose an operational stage-transition, disposition, restore, or configurable-stage workflow directly in the recruiter workbench. These observations confirm the user’s review and establish a redesign requirement rather than a cosmetic enhancement.

## Priority redesign domains

| Domain | Current boundary | Required operational redesign |
|---|---|---|
| Requisition | Minimal creation form with basic planning fields | Full hiring plan, ownership, department/cost-center, employment and location data, compensation visibility, target hiring dates, approval, posting, application form, evaluation plan, and compliance controls. |
| Application operations | Read-only application cards in the main workbench | Filterable, stage-oriented pipeline board; candidate selection; stage movement; stage-specific activities; rejection and restoration; disqualification reasons; source and timeline context; immutable audit evidence. |
| Candidate CRM | Search and limited bulk actions | Candidate profile workbench, relationship and application history, duplicate review, consent, sourcing actions, tags/pools, activities, and recruiter task context. |
| Interview operations | Basic scheduled interview records and feedback | Interview plans, interview kits, interviewer assignments, availability/self-scheduling readiness, structured scorecards, feedback completion, and debrief workflow. |
| Offer and decisions | Internal offer drafts with independent final decision approval | Offer package, approval chain, versioned terms, candidate response record, and accepted-offer handoff—while keeping external delivery inactive until a provider is configured. |
| Recruiting intelligence | Existing reports and governed AI recommendations | Recruiter work queue, time-in-stage/bottleneck reporting, funnel conversion, source performance, SLA/task indicators, and explainable AI recommendations. |

## Governing constraints

Every redesign surface must remain organization scoped. Movement into a final hire/reject outcome remains independently approval-gated; record-only notifications remain non-delivered; job-board distribution remains draft-only; and no SSO or provider credential may be invented.
