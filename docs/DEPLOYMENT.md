# EAROS Production Deployment Runbook

EAROS must be deployed as a **separate frontend and API service** with a managed MongoDB-compatible database. The API container is defined in `backend/Dockerfile`; the frontend must be built with an API base URL that points only to the intended EAROS API origin.

## Required production configuration

| Variable | Requirement |
| --- | --- |
| `EAROS_ENV` | Set to `production`. This disables interactive API documentation and requires an explicit CORS allowlist. |
| `MONGO_URL` | A TLS-enabled, least-privilege production database connection string. Never commit it. |
| `DB_NAME` | A dedicated EAROS production database name. |
| `CORS_ORIGINS` | Comma-separated, exact browser origins, for example `https://app.example.com`. Wildcards are rejected in production. |
| `AUTH_SESSION_DATA_URL` | The approved upstream identity-session validation endpoint. |
| `EAROS_COOKIE_SECURE` | `true` in production. |
| `EAROS_COOKIE_SAMESITE` | Normally `lax`; use `none` only for a documented cross-site architecture over HTTPS. |
| `EAROS_ALLOW_JIT_PROVISIONING` | `false` unless identity claims include a reviewed organization assignment. |
| `EAROS_ENABLE_DEV_LOGIN` | `false`. |
| `EAROS_ENABLE_BOOTSTRAP_ENDPOINT` | `false` after the controlled migration/bootstrap window ends. |
| `EAROS_BOOTSTRAP_SECRET` | A high-entropy secret set only for the controlled bootstrap window, then removed or rotated. |

## Deployment sequence

1. Run the repository security contract in CI and require a passing review.
2. Provision a managed database with encrypted transport, restricted network access, backups, and separate staging and production databases.
3. Add production variables through the deployment platform’s secret manager; do not create `.env` files in the image or repository.
4. Deploy the API using `backend/Dockerfile`, expose it through TLS, and configure an authenticated health probe for `/api/health` if the platform supports it.
5. Deploy the frontend with the exact API origin. Add only the frontend origin to `CORS_ORIGINS`.
6. Set `EAROS_ENABLE_BOOTSTRAP_ENDPOINT=true` only during the approved initial bootstrap, provide the bootstrap secret as an HTTP header, confirm the expected organization/policies exist, and disable the endpoint immediately afterward.
7. Verify a real user receives an explicit organization and supported role; verify no developer-login route responds in production.
8. Confirm event, approval, execution, and reflection queries remain organization-scoped for two separate test tenants.

## Go-live criteria

- No wildcard CORS origin exists in the production configuration.
- No demo or developer login is enabled.
- Production sessions persist only token hashes, use secure HTTP-only cookies, and expire according to the configured TTL.
- Every administrator, recruiter, hiring manager, executive, and candidate identity is explicitly mapped to the correct organization.
- Backup restore, access revocation, incident ownership, uptime alerting, and deployment rollback are documented by the operating team.
- External recruiting-system credentials are connected only after each provider’s authorization terms and data-processing requirements are approved.
