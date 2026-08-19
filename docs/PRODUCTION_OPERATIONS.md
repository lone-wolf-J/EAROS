# EAROS Production Operations

EAROS is deployed as two independently scalable services: a React client and a FastAPI API backed by MongoDB. The client embeds only the public API origin at build time; all credentials remain in the API runtime environment.

## Required operator configuration

| Setting | Where it belongs | Notes |
| --- | --- | --- |
| `VITE_BACKEND_URL` | Frontend build | Public `https://` origin only; it is embedded in browser code. |
| `MONGO_URL` | API runtime | Use a TLS-enabled managed MongoDB connection and a least-privilege database user. |
| `CORS_ORIGINS` | API runtime | Comma-separated explicit EAROS client origins. Wildcards are rejected in production. |
| `EAROS_SESSION_SECRET` | API runtime | Long, randomly generated secret managed by the deployment secret store. |
| `EAROS_BOOTSTRAP_SECRET` | API runtime | Separate one-time provisioning secret; never expose to the client. |
| `EAROS_ENABLE_DEV_LOGIN` | API runtime | Keep `false` in every non-development environment. |
| `EAROS_ENABLE_BOOTSTRAP_ENDPOINT` | API runtime | Keep `false` except for a controlled initial provisioning window. |

## First deployment sequence

1. Provision managed MongoDB with encryption at rest, TLS, automated backups, point-in-time recovery, and a non-administrative application user.
2. Create the API secrets in the deployment provider’s secret store. Do not commit `.env` files.
3. Build and deploy the API. Confirm `/api/ready` returns a successful database readiness response.
4. Build the client using the deployed public API URL. Deploy it behind TLS using the included static-serving container or an equivalent managed static host.
5. Set `CORS_ORIGINS` to the exact deployed client URL and validate a signed-in browser session.
6. During an access-controlled maintenance window, set the bootstrap endpoint flag and secret, create the initial organization administrator, then immediately disable the flag.
7. Run the security-contract suite and capture the deployed version, migration state, and readiness result in the change record.

## Operational controls

* Use unique production, staging, and development databases. Do not share user, session, approval, or audit collections between environments.
* Retain immutable execution, approval, and governance events according to the organization’s legal and hiring-retention policies.
* Monitor API readiness, latency, 4xx/5xx rates, authentication failures, authorization denials, policy denials, approval queue age, and MongoDB saturation.
* Rotate session and bootstrap secrets through the deployment secret store. Rotate API credentials after any suspected disclosure.
* Treat resume files, candidate data, and generated evaluations as sensitive personal data. Apply tenant filtering at every API and database access point.
