#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=(docker compose -f "$ROOT_DIR/docker-compose.infrastructure-smoke.yml" -f "$ROOT_DIR/docker-compose.infrastructure-auth-smoke.yml" -p earos-infrastructure-browser-smoke)
SMOKE_OUTPUT="${EAROS_BROWSER_SMOKE_OUTPUT:-/tmp/earos-infrastructure-browser-smoke}"

cleanup() {
  "${COMPOSE[@]}" logs --no-color > /tmp/earos-infrastructure-browser-smoke.log 2>&1 || true
  "${COMPOSE[@]}" down --volumes --remove-orphans || true
}
trap cleanup EXIT

rm -rf "$SMOKE_OUTPUT"
mkdir -p "$SMOKE_OUTPUT"
"${COMPOSE[@]}" up --build --wait --wait-timeout 180

curl --fail --silent --show-error \
  -H "X-Bootstrap-Secret: infrastructure-auth-smoke-only" \
  -X POST http://127.0.0.1:18000/api/bootstrap > /dev/null

pushd "$ROOT_DIR/frontend" > /dev/null
npx playwright install chromium
EAROS_BROWSER_API_BASE=http://127.0.0.1:18080 \
EAROS_BROWSER_WEB_BASE=http://127.0.0.1:18080 \
EAROS_BROWSER_SMOKE_OUTPUT="$SMOKE_OUTPUT" \
yarn test:browser-smoke
popd > /dev/null

echo "EAROS self-contained authenticated browser smoke validation passed."
