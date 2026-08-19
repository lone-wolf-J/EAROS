# EAROS — Governed Recruitment Operating System

EAROS is a governed, enterprise recruitment operating system. Its AI planner proposes actions; the deterministic policy and runtime layers decide whether an action may proceed, requires a human approval, or must be blocked.

## Production posture

This repository includes a production-hardening baseline for explicit organization assignment, hashed server-managed sessions, fail-closed production CORS, disabled-by-default developer and bootstrap routes, tenant-bound direct-resource access, and focused CI security-contract checks.

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for API environment configuration and go-live controls, [`docs/PRODUCTION_OPERATIONS.md`](docs/PRODUCTION_OPERATIONS.md) for the two-service deployment sequence, and [`docs/PRODUCTION_READINESS_AUDIT.md`](docs/PRODUCTION_READINESS_AUDIT.md) for the implementation risk assessment.

## Client deployment

The React client is a separately deployable Vite production image under `frontend/`. Build it with an explicit public `VITE_BACKEND_URL`; the API URL is browser-visible, but every credential remains exclusively in the API service’s runtime secret store. The checked-in `frontend/yarn.lock` makes client dependency installation reproducible.
