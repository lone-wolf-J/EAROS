#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.infrastructure-smoke.yml"
COMPOSE=(docker compose -f "$COMPOSE_FILE" -p earos-infrastructure-smoke)

cleanup() {
  "${COMPOSE[@]}" logs --no-color > /tmp/earos-infrastructure-smoke.log 2>&1 || true
  "${COMPOSE[@]}" down --volumes --remove-orphans || true
}
trap cleanup EXIT

"${COMPOSE[@]}" up --build --wait --wait-timeout 180

api_payload="$(curl --fail --silent --show-error http://127.0.0.1:18000/api/ready)"
web_payload="$(curl --fail --silent --show-error http://127.0.0.1:18080/)"

node -e '
const payload = JSON.parse(process.argv[1]);
if (!payload.ok || payload.service !== "EAROS" || payload.kind !== "readiness") process.exit(1);
' "$api_payload"

if ! grep --quiet "EAROS" <<<"$web_payload"; then
  echo "EAROS frontend container did not serve the expected application shell" >&2
  exit 1
fi

echo "EAROS self-contained infrastructure smoke validation passed."
