# EAROS Frontend Release Verification

**Scope:** Vite production artifact validation for the EAROS frontend after the CRACO migration.

> This record validates build output and static SPA fallback behavior. It does **not** claim that a production container image was built, because Docker runtime tooling was unavailable in the validation environment.

| Control | Result | Evidence |
| --- | --- | --- |
| Release configuration | Verified | The frontend Dockerfile builds with Node 22, sets `NODE_ENV=production`, passes `VITE_BACKEND_URL` at build time, and serves `/app/dist` with Nginx. |
| Deployment contract | Passed | `yarn verify:deployment-contract` statically verifies the committed Yarn 1 lockfile, direct Vite build, frozen-lockfile installation, public-API build input, no environment-file copy, non-root API runtime, health endpoints, browser security headers, Compose readiness ordering, and documentation prerequisites. |
| Vite production build | Passed | `VITE_BACKEND_URL=https://api.example.invalid yarn build` completed successfully and emitted `dist/index.html` plus route-split assets. |
| Development-host override resistance | Passed | `NODE_ENV=development VITE_BACKEND_URL=https://api.example.invalid yarn build && yarn verify:release-artifact` still emitted the production Vite artifact and contained no CRACO, React Refresh, Webpack development-server, or inherited visual-editor runtime markers. Vite release mode is selected by the build command rather than the host shell's inherited `NODE_ENV`. |
| Static route fallback | Passed | The Vite preview returned HTTP 200 and the SPA index shell for `/`, `/careers`, `/ats`, `/ats/workflows`, and `/enterprise-controls`. |
| Protected-route behavior | Bounded check passed | The protected URLs return the SPA shell; actual session enforcement remains a browser/runtime responsibility of `Protected` and `AuthProvider`. |
| Isolated browser landing check | Passed | A production Vite preview with the safe placeholder API origin rendered the EAROS landing route in the isolated browser, including the governed-runtime architecture and demo-role entry controls. |
| Isolated protected-route fallback | Bounded check passed | An unauthenticated request to `/ats` resolved to the controlled public landing state rather than a server error. This confirms the SPA routing boundary only; it does not substitute for an authenticated tenant workflow against a live API. |
| Container image build | Deferred | Docker is not installed in the current validation environment, so image build, Nginx health check, and Compose readiness sequencing remain an explicit pre-release verification step. |

## Reproduction

Run the following from `frontend/` with a deployment-safe API origin injected by CI or the deployment environment:

```bash
VITE_BACKEND_URL=https://api.example.invalid yarn build
NODE_ENV=development VITE_BACKEND_URL=https://api.example.invalid yarn build
yarn verify:release-artifact
yarn verify:deployment-contract
yarn preview --host 0.0.0.0 --port 4173
```

Then request representative public and protected routes. The static server should serve the SPA entrypoint while client-side routing and authentication determine the final view.

For an isolated browser check, run the preview with the same safe placeholder origin and confirm the landing route renders. Without a live authenticated API session, protected-route checks are limited to confirming a controlled public/authentication state rather than a server routing error.

## Release gate

Before production promotion, the release operator must build the frontend image, verify the Nginx health check, and exercise the listed routes with an authenticated tenant session against the intended API deployment. No provider credentials, SSO metadata, or candidate records are needed for the artifact-only checks above.
