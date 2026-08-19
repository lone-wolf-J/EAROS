# EAROS Production Readiness Audit

**Source repository:** [lone-wolf-J/EAROS](https://github.com/lone-wolf-J/EAROS)

**Review basis:** A read-only static review of the cloned repository before application execution.

## Confirmed baseline

EAROS is a React 19 client built with CRACO, React Router, React Query, Tailwind, Radix UI, and Framer Motion. Its backend is a FastAPI application with a MongoDB/Motor data layer, policy and governance services, modular recruiting-intelligence services, and a runtime intended to gate business actions.[1]

The design intent and product surfaces are mature for a demonstration: mission control, hiring intake, sourcing, resume analysis, screening, outreach, interview workflow, policy, approvals, governance, scenarios, and reflection are represented in the repository.[1]

## Immediate production risks

| Priority | Finding | Production effect | Required remediation |
| --- | --- | --- | --- |
| Critical | The authentication module derives roles from email fragments and assigns every first-time user to `org_levelshift`. | A malicious or accidental email pattern could result in inappropriate privileges and cross-customer data assignment. | Replace heuristic role assignment with organization membership records and approved identity claims. |
| Critical | A `/api/auth/dev-login` route mints sessions for embedded demonstration users. | Demo credentials remain an application authentication path. | Disable the route by default and permit it only in an explicitly marked non-production environment. |
| Critical | The bootstrap endpoint is unauthenticated and seeds demonstration data/users. | A production deployment could expose or pollute tenant data. | Remove it from the default public surface and limit bootstrap to a controlled administrative command. |
| High | CORS falls back to `*` while credentialed requests are enabled. | Browser trust boundaries are unsafe or inconsistent. | Require a configured origin allowlist in production and fail closed when it is absent. |
| High | Several direct-resource routes fetch a job or candidate by ID without proving that the record belongs to the authenticated user’s organization. | A guessed or leaked identifier could result in cross-tenant record access or mutation. | Add organization ownership checks to all direct-resource and intelligence routes. |
| High | API endpoints expose deterministic simulation and demonstration workflows alongside operational routes. | Demonstration outputs could be mistaken for real operational data. | Feature-gate simulation/demo features and label their data/provenance clearly. |
| Medium | The repository includes the legacy Create React App/CRACO toolchain. | Longer-term dependency and security maintenance burden. | Plan a Vite migration after core authorization hardening. |

## Production conversion approach

The first hardening release should focus on secure identity, tenant isolation, locked-down configuration, governed administrative operations, and regression tests for authorization. It should not attempt a wholesale UI rewrite or replace the existing policy/runtime architecture.

> The existing EAROS architecture’s principle that the planner proposes and the runtime executes through policy controls should remain intact; the production release must apply the same discipline to HTTP routes and identity operations.[1]

## References

[1]: https://github.com/lone-wolf-J/EAROS "User-approved EAROS source repository"
