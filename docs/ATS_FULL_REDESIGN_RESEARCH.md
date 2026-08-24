# EAROS Full Operational ATS Redesign — Research Notes

**Scope.** This note captures official product evidence used to distinguish a minimal recruiting interface from an operational enterprise ATS. It does not treat vendor marketing as a security or compliance requirement; the implementation decision remains constrained by EAROS tenant isolation, approval gates, audit evidence, and the owner-confirmed record-only provider posture.

## Enterprise workflow evidence

Workday describes a talent-acquisition suite that combines candidate engagement, recruiter and candidate experiences, hiring-team collaboration, high-volume workflows, interview management, reporting/compliance, internal mobility, evergreen requisitions, bulk offer processing, candidate status, and self-selected interview times.[1] Its recruiting hub concept also emphasizes work queues and recruiter task completion rather than a single job-description form.[1]

Greenhouse describes a candidate portal, job alerts, easy applications, transparent status, interview self-scheduling, structured interview plans, video-conference integration, candidate surveys, pipeline-history reporting, and per-job flexible pipelines.[2] Its structured-hiring guidance pairs scheduled interviews with interview kits, reusable job templates, criteria-based scorecards, feedback completion, offer approvals, and retrospective debriefs.[3] Greenhouse’s scorecard guidance further identifies consistent job criteria, purposeful interview questions, and comparable evaluation data as a core hiring quality control.[4]

## Design implications for EAROS

The redesign must provide an operational recruiter workspace with personally actionable work, complete requisition planning and approvals, full candidate/application tracking, configurable pipelines and stage actions, interview plans and scorecards, offers and decision controls, reporting, and candidate-facing self-service. Provider-backed messaging, calendar, background checks, and e-signature may remain configured-but-inactive until an owner supplies approved providers; EAROS must still preserve auditable records and never fabricate delivery.

## References

[1]: https://www.workday.com/en-us/products/talent-management/talent-acquisition.html "Workday Talent Acquisition Software"
[2]: https://www.greenhouse.com/candidate-experience "Greenhouse Candidate Experience"
[3]: https://support.greenhouse.io/hc/en-us/articles/360042755531-Informed-hiring-guide "Greenhouse Informed Hiring Guide"
[4]: https://www.greenhouse.com/guidance/how-focus-attributes-improve-comparability-of-interview-scorecards "Greenhouse Focus Attributes and Interview Scorecards"
