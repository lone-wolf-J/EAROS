# EAROS Frontend Release Verification

**Scope:** Vite production artifact validation for the EAROS frontend after the CRACO migration.

> This record validates build output and static SPA fallback behavior. It does **not** claim that a production container image was built, because Docker runtime tooling was unavailable in the validation environment.

| Control | Result | Evidence |
| --- | --- | --- |
| Release configuration | Verified | The frontend Dockerfile builds with Node 22, sets `NODE_ENV=production`, passes `VITE_BACKEND_URL` at build time, and serves `/app/dist` with Nginx. |
| Vite production build | Passed | `VITE_BACKEND_URL=https://api.example.invalid yarn build` completed successfully and emitted `dist/index.html` plus route-split assets. |
| Static route fallback | Passed | The Vite preview returned HTTP 200 and the SPA index shell for `/`, `/careers`, `/ats`, `/ats/workflows`, and `/enterprise-controls`. |
| Protected-route behavior | Bounded check passed | The protected URLs return the SPA shell; actual session enforcement remains a browser/runtime responsibility of `Protected` and `AuthProvider`. |
| Browser visual route check | Not available | The connected browser could not establish a local preview connection. Managed EAROS visual checks are recorded separately; this source-workspace record does not substitute for authenticated source-route review. |
| Container image build | Deferred | Docker is not installed in the current validation environment, so image build, Nginx health check, and Compose readiness sequencing remain an explicit pre-release verification step. |

## Reproduction

Run the following from `frontend/` with a deployment-safe API origin injected by CI or the deployment environment:

```bash
VITE_BACKEND_URL=https://api.example.invalid yarn build
yarn preview --host 0.0.0.0 --port 4173
```

Then request representative public and protected routes. The static server should serve the SPA entrypoint while client-side routing and authentication determine the final view.

## Release gate

Before production promotion, the release operator must build the frontend image, verify the Nginx health check, and exercise the listed routes with an authenticated tenant session against the intended API deployment. No provider credentials, SSO metadata, or candidate records are needed for the artifact-only checks above.
