#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/docker-compose.infrastructure-smoke.yml"
PROJECT_NAME="earos-backup-restore-smoke"
LOG_FILE="${TMPDIR:-/tmp}/earos-backup-restore-smoke.log"
BACKUP_DATABASE="earos_backup_restore_smoke"

cleanup() {
  docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs --no-color >"$LOG_FILE" 2>&1 || true
  docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down --volumes --remove-orphans || true
}
trap cleanup EXIT

cd "$ROOT_DIR"
docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up --detach mongo

for attempt in $(seq 1 30); do
  if docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -T mongo mongosh --quiet --eval 'db.runCommand({ ping: 1 }).ok' | grep -qx '1'; then
    break
  fi
  if [[ "$attempt" == "30" ]]; then
    echo "Disposable MongoDB backup/restore smoke database did not become ready" >&2
    exit 1
  fi
  sleep 2
done

docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -T mongo mongosh --quiet --eval "
  const database = db.getSiblingDB('${BACKUP_DATABASE}');
  database.recovery_cases.deleteMany({});
  database.recovery_cases.insertOne({
    recordId: 'backup-restore-contract',
    organizationId: 'org_backup_smoke',
    subject: 'disposable synthetic record',
    createdAt: new Date()
  });
  if (database.recovery_cases.countDocuments({ recordId: 'backup-restore-contract' }) !== 1) quit(1);
"

docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -T mongo sh -lc "mongodump --quiet --db '${BACKUP_DATABASE}' --archive=/tmp/earos-backup-restore-smoke.archive"

docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -T mongo mongosh --quiet --eval "db.getSiblingDB('${BACKUP_DATABASE}').dropDatabase()"

if docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -T mongo mongosh --quiet --eval "db.getSiblingDB('${BACKUP_DATABASE}').recovery_cases.countDocuments({})" | grep -qx '0'; then
  :
else
  echo "Disposable MongoDB backup/restore smoke did not clear its source database before restore" >&2
  exit 1
fi

docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -T mongo sh -lc "mongorestore --quiet --archive=/tmp/earos-backup-restore-smoke.archive"

if docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -T mongo mongosh --quiet --eval "db.getSiblingDB('${BACKUP_DATABASE}').recovery_cases.countDocuments({ recordId: 'backup-restore-contract', organizationId: 'org_backup_smoke' })" | grep -qx '1'; then
  echo "EAROS disposable MongoDB backup/restore smoke validation passed."
else
  echo "EAROS disposable MongoDB backup/restore smoke did not recover the tenant-scoped synthetic record" >&2
  exit 1
fi
