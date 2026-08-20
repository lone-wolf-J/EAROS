# EAROS Production Operations Runbook

## Purpose and operating boundary

This runbook defines the minimum operational controls for a production EAROS deployment. EAROS remains the governed recruiting system of record: operational availability must not bypass tenant scoping, role checks, policy evaluation, approval queues, or immutable governance events.

> **Do not treat a successful container start as a go-live approval.** A release is eligible only after the environment, authentication, readiness, tenant isolation, and governed workflow checks in this runbook have completed.

## Runtime topology and health semantics

| Component | Responsibility | Health signal | Failure response |
|---|---|---|---|
| `web` | Serves the Vite-built client through Nginx | Container health check on port `8080` | Remove from traffic and investigate deployment or static-asset failure. |
| `api` | FastAPI API, governed runtime, tenant-scoped access controls | `GET /api/health` proves liveness; `GET /api/ready` proves MongoDB connectivity | Do not route traffic to a replica that fails readiness. |
| MongoDB | External durable world-state, governance, and audit persistence | API readiness ping | Escalate to the database owner; do not run destructive repair commands from the application container. |
| Log aggregation | Receives JSON event stream from API standard output | `request_completed`, `request_failed`, and `readiness_failed` events | Retain correlation data; do not ingest request bodies, session tokens, authorization headers, or resume contents. |

The API provides a **liveness** endpoint at `/api/health`, which deliberately avoids a dependency check, and a **readiness** endpoint at `/api/ready`, which performs a MongoDB ping. The production Compose configuration waits for API readiness before starting the web service.

## Required production configuration

The deployment operator must inject configuration through the approved secret manager or deployment environment. Do not commit `.env` files, connection strings, bootstrap secrets, authentication tokens, or identity-provider material.

| Variable or control | Production expectation |
|---|---|
| `EAROS_ENV` | Set to `production`. This disables generated API documentation endpoints. |
| `MONGO_URL`, `DB_NAME` | Point to the production database owned by the production database account. Grant the least-privileged application role required by EAROS. |
| `CORS_ORIGINS` | Explicit comma-separated HTTPS origins only. Wildcards and an empty value are rejected in production. |
| `EAROS_PUBLIC_API_ORIGIN` | Public HTTPS API origin supplied as the frontend image build argument. |
| `EAROS_COOKIE_SECURE` | `true`. Use `EAROS_COOKIE_SAMESITE=none` only when cross-site cookies are genuinely required and HTTPS is in use. |
| `AUTH_SESSION_DATA_URL` | **Must be explicitly overridden** with the approved production identity-session endpoint. It must be an absolute HTTPS URL without embedded credentials, a query string, or fragment. EAROS refuses to start in production when this value is absent or still points to the inherited demonstration identity service. Treat it as an external dependency and monitor its availability separately. |
| `EAROS_ALLOW_JIT_PROVISIONING` | Keep disabled unless a documented enrollment window has been approved. If enabled, supply an explicit tenant assignment path. |
| `EAROS_ENABLE_DEV_LOGIN`, `EAROS_ENABLE_BOOTSTRAP_ENDPOINT` | Keep disabled. Bootstrap access must only be temporarily enabled during a controlled initial setup with a unique secret. |
| `EAROS_LOG_LEVEL` | Default to `INFO`; use `WARNING` for degraded log-collection capacity rather than suppressing error events. |
| `EAROS_OPERATIONS_METRICS_TOKEN` | Unique secret for the authorized observability collector. The collector must send it through `X-Operations-Token` to request bounded, non-tenant metrics from `/api/metrics`. |

## Deployment procedure

1. Build from a reviewed commit and confirm the exact release revision in the change record.
2. Populate deployment secrets through the platform secret store. Validate that no development, demonstration, or shared tenant configuration is present.
   Confirm `AUTH_SESSION_DATA_URL` names the approved production identity service and that `EAROS_ENABLE_DEV_LOGIN` is unset or `false`; production startup fails closed when either authentication boundary is unsafe.
3. Validate the Compose definition without starting a release:

   ```bash
   EAROS_PUBLIC_API_ORIGIN=https://api.example.com docker compose -f docker-compose.production.yml config
   ```

4. Build the API and frontend images. The API image must be built from the repository root so `backend/Dockerfile` can copy the locked backend requirements and source tree.
5. Deploy to a non-production environment first. Confirm liveness, readiness, authenticated tenant access, and a policy-queued governed action there.
6. Deploy the approved release to production. Keep rollback artifacts available until post-deployment verification succeeds.
7. Record the release revision, image identifiers, start time, configuration change ticket, verifier, and verification results in the deployment record.

## Post-deployment verification checklist

| Check | Expected result | Evidence to retain |
|---|---|---|
| `GET /api/health` | HTTP `200` with `ok: true` and `kind: liveness` | Timestamped response and deployed version. |
| `GET /api/ready` | HTTP `200` with `ok: true` and `kind: readiness` | Timestamped response; do not expose database details publicly. |
| Frontend load | Nginx returns the EAROS shell without JavaScript load errors | Browser capture or deployment monitor result. |
| Tenant boundary | A user cannot retrieve a candidate, requisition, or decision from another organization | Controlled cross-tenant negative test record. |
| Governance path | A policy-requiring action produces an approval queue record rather than an immediate destructive action | Execution ID and immutable governance event. |
| Correlation | Response carries `X-Request-ID`; matching JSON completion event appears in log aggregation | Request ID and redacted log event. |
| Integration posture | Job-board distribution remains draft-only without configured provider credentials | Administrator verification record. |

## Backup and restoration control

EAROS stores durable records in the configured external MongoDB service. The **database owner**, rather than an application container, must operate encrypted backups, define retention, and authorize restore access. The release owner must document the backup provider, recovery point objective, recovery time objective, backup cadence, and most recent tested restoration date before go-live.

Restoration is a controlled security event. Restore first to an isolated environment, restrict access to the recovery team, validate collection integrity and tenant boundaries, and record the recovery source and time window. Do not overwrite the production database until the incident commander, database owner, and EAROS security owner approve the cutover. Do not treat backup restoration as a substitute for the application’s audit-export or data-subject request workflows.

## Observability and incident response

The API emits JSON standard-output events containing an event name, level, timestamp, request identifier, HTTP method, path, response status, duration, and exception type where applicable. The middleware intentionally excludes request payloads and authentication material. Configure log aggregation with access controls and retention appropriate for operational metadata.

An approved observability collector can request `GET /api/metrics` with `X-Operations-Token`. The endpoint returns only process-start time, request and unexpected-failure counts, status-class counts, and bounded duration aggregates. It does not emit request identifiers, tenant identifiers, candidate information, routes with dynamic resource identifiers, request bodies, or credentials. Keep the collector credential in the same secret-management boundary as other production secrets and rotate it after suspected exposure.

| Alert condition | Initial action | Escalation and containment |
|---|---|---|
| Repeated `/api/ready` failures | Confirm MongoDB availability and credentials without printing secrets. | Remove unhealthy API instances from traffic; engage the database owner. |
| Elevated `request_failed` events | Group by `error_type`, path, deployed version, and `request_id`. | Roll back the release if the error began with deployment; preserve logs and execution IDs. |
| Suspected tenant-boundary violation | Stop affected release paths and preserve logs, audit events, and request IDs. | Notify security and product owners; investigate using immutable governance records. Do not alter evidence. |
| Suspicious governed action | Locate the execution and approval records before making changes. | Use the policy/approval controls to prevent further execution; do not bypass the runtime. |
| Credential exposure | Rotate affected credential through the secret manager and invalidate impacted sessions as appropriate. | Treat as a security incident; review access logs and deployment history. |

Every incident record must include a UTC timeline, affected tenant identifiers where appropriate, request and execution identifiers, containment actions, customer communication owner, root-cause findings, and follow-up remediation. Logs, governance events, and audit exports are evidence; avoid deletion or mutation during investigation.

## Go-live approval and rollback

Go-live requires written approval from the release owner, security owner, database owner, and business owner after the verification checklist succeeds. The approval must name the deployment revision and the rollback revision.

Rollback is preferred over in-place code repair for a failing release. Re-deploy the last verified image, then verify `/api/health`, `/api/ready`, authentication, tenant isolation, and one governed approval path. Database schema or data restoration requires a separately approved change because application rollback does not reverse durable data mutations.

## Deferred go-live dependencies

The following dependencies are intentionally not inferred, fabricated, or activated from source code. They are explicit production gates and remain inactive, draft-only, or unverified until the named operating owner supplies the required evidence.

| Dependency | Current posture | Required owner input and evidence | Activation boundary |
| --- | --- | --- | --- |
| SSO/SAML | Not activated. Production authentication rejects the demonstration identity endpoint and developer login remains disabled. | Identity administrator supplies IdP metadata, approved redirect/logout URLs, organization and role-claim mapping, certificate rotation plan, and a staged sign-in test record. | Security and release owners approve tenant-scoped SSO verification before enabling production sign-in. |
| Job-board delivery | Draft-only adapter readiness; no provider credential is stored or used. | Recruiting operations and security approve provider terms, data-processing review, tenant-scoped credentials, attribution rules, and controlled publishing evidence for each provider. | An administrator activates one approved provider at a time; human approval gates remain in force for publication. |
| Candidate notification delivery | Record-only; outbound provider delivery is disabled. | Communications owner supplies an approved provider, sending domain, template governance, consent/opt-out handling, data-processing review, and controlled delivery evidence. | Delivery may be enabled only after recipient consent and provider configuration are verified in the intended tenant. |
| Backup and restoration | Runbook policy exists; provider configuration and restoration evidence are not supplied in this workspace. | Database owner documents provider, encryption, cadence, retention, RPO/RTO, restore authorization, and an isolated-environment restoration test with date and evidence. | Go-live requires the documented and tested restoration control described above. |
| Container image and Compose runtime | Static Docker, Nginx, and Compose contracts pass; no Docker daemon is available in this validation environment. | Release owner provides CI or controlled-host evidence for image build, image scan, Nginx `/healthz`, API `/api/health` and `/api/ready`, Compose dependency sequencing, and rollback image reference. | Production promotion requires successful runtime evidence; static configuration verification is not a substitute. |
| Authenticated source-route workflow | Artifact and unauthenticated routing checks pass; no live identity/database service is attached to the isolated validation environment. | Release owner supplies a non-production tenant and authorized test identities to exercise sign-in, role mapping, tenant isolation, a governed approval, and a record-only offer workflow. | Evidence must be captured before production promotion; no authentication bypass is added for validation. |

> These deferred dependencies do not weaken the governed runtime. In their absence, EAROS continues to deny or record-only sensitive actions rather than send, publish, decide, or restore automatically.
