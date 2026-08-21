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

## Authenticated browser workflow

After the runtime command succeeds, use the same non-production test user in a browser. Sign in through the approved staging identity flow and capture the following evidence: ATS Operations loads, candidates and pipeline load for the allowed tenant, offers and interviews load without provider delivery, and a second-tenant candidate cannot be opened. Exercise one policy-requiring action only if the test tenant’s approval configuration has been reviewed; confirm that it produces an approval record rather than an immediate irreversible action.

## Completion rule

EAROS infrastructure validation is complete only when the release owner retains the command output, Compose logs, image references, browser captures, cross-tenant negative test result, and validated backup-restore evidence. Email delivery and SSO remain inactive until organization-owned providers and their separate activation evidence are available. The full operating boundary remains in [the production runbook](PRODUCTION_RUNBOOK.md).
