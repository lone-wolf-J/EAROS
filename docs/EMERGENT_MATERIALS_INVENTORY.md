# EAROS User-Provided Application Materials Inventory

## Purpose and Intake Boundary

This document records the materials available for the EAROS enhancement effort and the disposition of each category. The approved transferable input is the `lone-wolf-J/EAROS` repository clone. It is inventoried without executing imported code during intake, as recorded in [the source workspace inventory](./SOURCE_WORKSPACE_INVENTORY.md).

The inventory supports the architectural decision to extend EAROS in place rather than merge the parallel managed ATS prototype into its system of record. That decision and its governance constraints are recorded in [the ATS implementation decision](./ATS_IMPLEMENTATION_DECISION.md).

## Artifact Inventory

| Category | Available materials | Usable disposition | Explicit boundary |
| --- | --- | --- | --- |
| Source code | `backend/` FastAPI services, governed platform core, domain contracts, and backend tests; `frontend/` React/Vite client, route contracts, and build scripts. | Primary implementation baseline for EAROS product work. The governed planner, deterministic policy evaluator, approval persistence, execution runtime, and tenant-scoped ATS world state are retained and extended in place. | Dependency directories, virtual environments, caches, compiled outputs, and generated test reports are not transferable source artifacts. |
| Data | No database dump, customer export, candidate-resume corpus, provider payload, or production tenant dataset was supplied in the approved source boundary. | Synthetic fixtures and contract-test records only; no customer data is imported or seeded. | Live MongoDB data and credential-protected external service data remain outside the repository and must not be copied into source control. |
| Configuration | Root deployment configuration and client/server build configuration are present, including `docker-compose.production.yml`, Vite configuration, package manifests, and documented environment-variable names. | Used to harden reproducible builds, production checks, and deployment documentation. | `.env` variants, secret values, certificates, private keys, SAML metadata, job-board credentials, and provider tokens are intentionally excluded and must be injected by the deployment secret manager. |
| Documentation | Production, frontend release, governed operationalization, product branding, deployment, and readiness records in `docs/`. | Used as the operating and migration record for EAROS implementation, validation, and go-live planning. | Documentation describes configuration requirements but never stores credentials or customer data. |
| Functional reference | The separately managed EAROS workspace provides tRPC/Drizzle ATS behavior contracts and UI-reference validation. | Used only as a functional reference and independent test surface for ATS workflows and authorization controls. | It is not a live EAROS data source and is not merged into the FastAPI/MongoDB product system of record. |

## Missing Inputs and Required Handling

No verified production data export, identity-provider metadata, provider credentials, backup-provider configuration, or container-runtime evidence is present in the source intake. These inputs cannot be inferred or fabricated. They remain deployment-time responsibilities and must be supplied through approved secret-management and operational channels.

> The absence of a material in this inventory is an explicit non-availability finding, not evidence that the material does not exist elsewhere.

## Migration Traceability

The material classification above leads directly to the implementation boundary: EAROS retains its existing governed architecture; the managed reference validates discrete ATS interaction and authorization patterns; and external production integrations are represented only by readiness controls until an authorized administrator provides the required configuration. This maintains tenant isolation, deterministic policy enforcement, human approval gates, and immutable auditability throughout the migration.
