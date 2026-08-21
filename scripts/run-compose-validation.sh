#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-ops/staging-validation.env}"
COMPOSE_FILE="${EAROS_COMPOSE_FILE:-docker-compose.production.yml}"
EVIDENCE_DIR="${EAROS_VALIDATION_EVIDENCE_DIR:-/tmp/earos-infrastructure-validation}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "EAROS infrastructure validation requires a controlled environment file. Copy ops/staging-validation.env.example to $ENV_FILE and populate it outside source control." >&2
  exit 2
fi

mkdir -p "$EVIDENCE_DIR"
set -a
source "$ENV_FILE"
set +a

export EAROS_VALIDATION_MODE="compose-local"
export EAROS_PUBLIC_API_ORIGIN="${EAROS_PUBLIC_API_ORIGIN:-http://127.0.0.1:8000}"
export EAROS_STAGING_WEB_ORIGIN="${EAROS_STAGING_WEB_ORIGIN:-http://127.0.0.1:8080}"

cleanup() {
  docker compose -f "$COMPOSE_FILE" logs --no-color > "$EVIDENCE_DIR/compose.log" 2>&1 || true
  docker compose -f "$COMPOSE_FILE" down --remove-orphans >> "$EVIDENCE_DIR/compose.log" 2>&1 || true
}
trap cleanup EXIT

docker compose -f "$COMPOSE_FILE" config > "$EVIDENCE_DIR/compose-config.yml"
docker compose -f "$COMPOSE_FILE" up --build --detach

for _ in $(seq 1 30); do
  if curl --fail --silent "${EAROS_PUBLIC_API_ORIGIN}/api/ready" > "$EVIDENCE_DIR/api-ready.json" && curl --fail --silent "${EAROS_STAGING_WEB_ORIGIN}/healthz" > "$EVIDENCE_DIR/web-health.txt"; then
    break
  fi
  sleep 4
done

curl --fail --silent "${EAROS_PUBLIC_API_ORIGIN}/api/ready" > "$EVIDENCE_DIR/api-ready.json"
curl --fail --silent "${EAROS_STAGING_WEB_ORIGIN}/healthz" > "$EVIDENCE_DIR/web-health.txt"
node scripts/validate-infrastructure.mjs --runtime --env-file "$ENV_FILE" | tee "$EVIDENCE_DIR/runtime-validation.txt"
docker compose -f "$COMPOSE_FILE" ps > "$EVIDENCE_DIR/compose-ps.txt"
echo "EAROS Compose validation passed. Redacted evidence is available at $EVIDENCE_DIR."
