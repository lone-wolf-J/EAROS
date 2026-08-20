# EAROS Frontend Configuration Boundary

The EAROS Vite client derives its API base from **`VITE_BACKEND_URL`** at build time. This setting is public configuration, not a secret: it is compiled into the browser artifact and must therefore contain only the HTTPS origin of the deployed EAROS API.

| Environment | Accepted value | Release behavior |
| --- | --- | --- |
| Development | Empty, `http://localhost:<port>`, or an HTTPS API origin | An empty value preserves relative `/api` requests for a colocated development proxy. |
| Production | `https://api.example.com` | Required; the client rejects missing, malformed, credential-bearing, path-bearing, query-bearing, fragment-bearing, or non-HTTPS values. |

The value must never embed an API key, username, password, tenant identifier, path, query string, or fragment. Session credentials continue to flow only as HTTP-only cookies through the existing client configuration.

> Build with `VITE_BACKEND_URL=https://api.example.invalid yarn build` for configuration validation. Vite rejects an unsafe production value before bundling. Replace the placeholder with the controlled production API origin only in the deployment system.
