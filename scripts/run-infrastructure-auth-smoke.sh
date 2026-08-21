#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=(docker compose -f "$ROOT_DIR/docker-compose.infrastructure-smoke.yml" -f "$ROOT_DIR/docker-compose.infrastructure-auth-smoke.yml" -p earos-infrastructure-auth-smoke)
COOKIE_JAR="$(mktemp)"

cleanup() {
  "${COMPOSE[@]}" logs --no-color > /tmp/earos-infrastructure-auth-smoke.log 2>&1 || true
  "${COMPOSE[@]}" down --volumes --remove-orphans || true
  rm -f "$COOKIE_JAR"
}
trap cleanup EXIT

"${COMPOSE[@]}" up --build --wait --wait-timeout 180

curl --fail --silent --show-error \
  -H "X-Bootstrap-Secret: infrastructure-auth-smoke-only" \
  -X POST http://127.0.0.1:18000/api/bootstrap > /dev/null

curl --fail --silent --show-error \
  -c "$COOKIE_JAR" \
  -X POST "http://127.0.0.1:18000/api/auth/dev-login?email=demo.recruiter%40levelshift.ai" > /dev/null

assert_tenant_response() {
  local path="$1"
  local payload
  payload="$(curl --fail --silent --show-error -b "$COOKIE_JAR" "http://127.0.0.1:18000${path}")"
  node -e '
const payload = JSON.parse(process.argv[1]);
if (payload && typeof payload === "object" && !Array.isArray(payload) && payload.organization_id && payload.organization_id !== "org_levelshift") process.exit(1);
' "$payload"
}

me_payload="$(curl --fail --silent --show-error -b "$COOKIE_JAR" http://127.0.0.1:18000/api/auth/me)"
node -e '
const user = JSON.parse(process.argv[1]);
if (user.email !== "demo.recruiter@levelshift.ai" || user.organization_id !== "org_levelshift" || user.role !== "recruiter") process.exit(1);
' "$me_payload"

assert_tenant_response "/api/world/organization"
assert_tenant_response "/api/ats/requisitions"
assert_tenant_response "/api/ats/candidates"
assert_tenant_response "/api/ats/pipelines"
assert_tenant_response "/api/ats/offers"
assert_tenant_response "/api/ats/interviews"

echo "EAROS self-contained authenticated infrastructure smoke validation passed."
