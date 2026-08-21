# EAROS Infrastructure Validation Package

## Purpose

This package converts EAROS’s production runbook into reproducible checks without storing secrets, creating an identity provider, or touching a production database. It validates the container topology, FastAPI liveness/readiness, Nginx health and SPA fallback, authenticated non-destructive recruiting reads, cross-tenant denial, and backup-restore evidence.

> Run the package only against an **isolated non-production tenant**. It does not create candidates, change application stages, publish jobs, send notifications, decide approvals, or restore over production data.

## What EAROS needs from you

| Item | Simple requirement | Where it goes |
| --- | --- | --- |
| A staging database | A separate MongoDB database or cluster, not production. | Deployment secret manager or the untracked `backend/.env` used only for staging. |
| A staging identity endpoint | A real HTTPS session/identity endpoint approved by your team. It can be added later; do not use developer login in production. | `AUTH_SESSION_DATA_URL` in the staging secret manager. |
| Two test records | One recruiter/admin test user in the allowed tenant, plus one candidate ID belonging to a different tenant. | The token and IDs in an untracked `ops/staging-validation.env`. |
| Docker-capable host or CI runner | Docker Engine with Docker Compose v2. | A staging host, CI pipeline, or controlled developer machine. |
| Backup owner evidence | A database owner completes one encrypted backup and restores it into an isolated recovery target. | An untracked JSON evidence file copied from `ops/backup-restore-evidence.example.json`. |

## Setup

Copy the non-secret templates and populate the real values only in a controlled environment:

```bash
cp ops/staging-validation.env.example ops/staging-validation.env
cp ops/backup-restore-evidence.example.json /secure/path/backup-restore-evidence.json
chmod 600 ops/staging-validation.env /secure/path/backup-restore-evidence.json
```

Create `backend/.env` only on the controlled host with the staging database, session boundary, secure cookie policy, CORS origin, and EAROS secrets required by the production Compose file. Do not commit either file.

## Validation commands

First, run a non-destructive preflight that rejects placeholder values, unsafe origins, and the inherited demonstration identity endpoint:

```bash
node scripts/validate-infrastructure.mjs --env-file ops/staging-validation.env
```

On a Docker-capable staging host, run the Compose test. It builds the images, waits for API readiness and Nginx health, probes public SPA routes, performs authenticated recruiting reads, confirms cross-tenant candidate access is denied, writes redacted runtime evidence under `/tmp/earos-infrastructure-validation`, and tears the stack down.

```bash
bash scripts/run-compose-validation.sh ops/staging-validation.env
```

The database owner then records an encrypted backup and an isolated restore before validating the evidence shape. This command intentionally verifies **evidence**, not provider credentials or backup contents.

```bash
node scripts/verify-backup-evidence.mjs /secure/path/backup-restore-evidence.json
```

## Docker-capable validation options

The repository includes a manual workflow at `.github/workflows/infrastructure-validation.yml`. It always checks the validation package on relevant changes. Its Docker runtime job runs only when a maintainer manually selects `run_runtime=true`; it reads non-production values only from the dedicated `earos-staging` environment.

The same workflow also runs `scripts/run-infrastructure-smoke.sh` on a hosted Docker-capable runner for every relevant push or pull request. This self-contained job builds the API and frontend images, starts an ephemeral MongoDB 7 service, verifies the API readiness endpoint, verifies that Nginx serves the EAROS application shell, saves Docker logs as a CI artifact, and removes its containers and volumes. It does not provision users, invoke the upstream identity service, contact a job board, or use organization secrets.

It then runs `scripts/run-infrastructure-auth-smoke.sh` against a distinct disposable Compose project. That project explicitly uses `EAROS_ENV=development`, enables the development-only login and bootstrap endpoints, and uses an ephemeral MongoDB volume. The script provisions only the seeded synthetic recruiter, verifies the authenticated tenant identity, and performs read-only requisition, candidate, pipeline, offer, and interview checks. This job validates the approved pseudo-login path without enabling it in the production smoke stack or substituting it for SSO validation.

The self-contained API, MongoDB, Nginx, compiled-route, and authenticated-read smoke suite passed on the hosted runner for commit `b31d63b` ([run 32435607511](https://github.com/lone-wolf-J/EAROS/actions/runs/32435607511)). This is reproducibility evidence for the container images and disposable synthetic environment; it is not evidence that any organization-owned email, SSO, backup, or production identity provider has been activated.

The hosted workflow also runs `scripts/run-infrastructure-browser-smoke.sh`. It uses the same disposable development-only auth overlay, signs in only the seeded synthetic recruiter, and drives Chromium against the compiled Nginx image. It captures screenshots after the recruiter successfully loads ATS Operations, ATS Autonomy, and the AI Interview Suite. The browser check is isolated from the production smoke stack, does not contact external identity or messaging systems, and retains images and Compose logs only as CI artifacts.

The hosted Chromium workflow passed for commit `13114ec` ([run 32439766822](https://github.com/lone-wolf-J/EAROS/actions/runs/32439766822)). It verifies a same-origin development-only synthetic session through the Nginx proxy, confirms that the session cookie is accepted by the compiled client’s normal authentication check, and renders the tenant-scoped ATS Operations, ATS Autonomy, and AI Interview Suite roots. The loopback HTTP exception is compile-time gated to this disposable smoke environment; ordinary production frontend builds continue to require an HTTPS API origin. This evidence validates the compiled browser workflow, but it does not activate an organization identity provider, outbound messaging, or a production database.

The expanded authenticated route suite passed for commit `1f1cf4d` ([run 32440400717](https://github.com/lone-wolf-J/EAROS/actions/runs/32440400717)). In addition to the compiled route roots, it opens the Candidate CRM, Applications pipeline, Interviews, and Offers workspaces within ATS Operations, waits for each stable workspace root, and saves browser evidence. The test operates solely with the disposable recruiter and empty or synthetic tenant records, so it proves protected UI composition and authenticated navigation rather than a provider-backed hiring transaction.

The same hosted smoke job also runs `scripts/run-backup-restore-smoke.sh`. It starts only a disposable MongoDB container, writes one tenant-scoped synthetic recovery record, creates a `mongodump` archive, drops the disposable database, restores the archive with `mongorestore`, and verifies the exact synthetic record was recovered. It captures local Compose logs and removes the entire temporary project and volumes. This validates executable backup-and-restore mechanics without handling organization data; production backup retention, encryption ownership, access control, and restoration evidence remain subject to the separate provider-controlled procedure.

The disposable recovery check passed on the hosted runner for commit `d40dde5` ([run 32435966679](https://github.com/lone-wolf-J/EAROS/actions/runs/32435966679)).

The API’s optional `emergentintegrations` client is intentionally not part of the required container dependency set because it is unavailable from the public Python package index. EAROS imports it dynamically only for optional model-backed planning and intake; when it is unavailable, the governed planner and intake path use their deterministic fallback behavior. A production deployment that has an approved internal package source may install that enhancement separately after the base image, but it must not weaken the self-contained operational baseline.

| Approach | Tradeoffs | Cost | Setup complexity |
| --- | --- | --- | --- |
| Run on your staging host | The nearest match to the eventual deployment; the database and identity endpoint can remain inside your private network. | Uses your existing staging host. | Copy the two templates, create the non-production records, and run one command. |
| Run the manual repository workflow | Uses a temporary Docker-capable runner and retains the workflow log as evidence; the staging database must be reachable from that runner. | Uses your repository’s CI allowance. | Add the two multiline secrets to the dedicated `earos-staging` environment, then manually run the workflow. |

Run the self-contained stack locally on any Docker-capable host with:

```bash
bash scripts/run-infrastructure-smoke.sh
```

For the manual workflow, add these **environment secrets**, never repository variables or source files:

| Secret | Contents |
| --- | --- |
| `EAROS_STAGING_BACKEND_ENV` | The complete non-production `backend/.env` content, including a staging database URL, explicit non-demo HTTPS identity endpoint, explicit CORS origin, and EAROS runtime secrets. |
| `EAROS_STAGING_VALIDATION_ENV` | The populated `ops/staging-validation.env` content containing local Compose origins, a least-privileged non-production session token, allowed-tenant ID, and a real different-tenant candidate ID. |

The workflow writes these values only to temporary ignored files, executes `scripts/run-compose-validation.sh`, captures redacted logs under `/tmp`, and removes the temporary files even when a check fails. Review the logs and preserve them with the release evidence; do not expose either secret in tickets, chat, or source control.

## Authenticated browser workflow

After the runtime command succeeds, use the same non-production test user in a browser. Sign in through the approved staging identity flow and capture the following evidence: ATS Operations loads, candidates and pipeline load for the allowed tenant, offers and interviews load without provider delivery, and a second-tenant candidate cannot be opened. Exercise one policy-requiring action only if the test tenant’s approval configuration has been reviewed; confirm that it produces an approval record rather than an immediate irreversible action. The hosted browser smoke is a disposable pseudo-login check only; it does not replace this organization-owned staging evidence.

## Completion rule

EAROS infrastructure validation is complete only when the release owner retains the command output, Compose logs, image references, browser captures, cross-tenant negative test result, and validated backup-restore evidence. Email delivery and SSO remain inactive until organization-owned providers and their separate activation evidence are available. The full operating boundary remains in [the production runbook](PRODUCTION_RUNBOOK.md).
