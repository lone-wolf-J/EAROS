import { readFileSync } from "node:fs";

const evidencePath = process.argv[2];
if (!evidencePath) throw new Error("Usage: node scripts/verify-backup-evidence.mjs <backup-restore-evidence.json>");

const evidence = JSON.parse(readFileSync(evidencePath, "utf8"));
const requiredStrings = ["environment", "provider", "backupId", "backupCompletedAt", "restoreTarget", "restoreCompletedAt", "verifiedBy"];
for (const key of requiredStrings) {
  if (typeof evidence[key] !== "string" || !evidence[key].trim() || /replace|example/i.test(evidence[key])) {
    throw new Error(`EAROS backup evidence failed: ${key} must contain recorded evidence, not a placeholder`);
  }
}
if (evidence.environment !== "staging" && evidence.environment !== "isolated-recovery") {
  throw new Error("EAROS backup evidence failed: restore evidence must come from staging or an isolated recovery environment");
}
for (const key of ["backupCompletedAt", "restoreCompletedAt"]) {
  if (Number.isNaN(Date.parse(evidence[key]))) throw new Error(`EAROS backup evidence failed: ${key} must be an ISO-8601 timestamp`);
}
for (const key of ["encrypted", "tenantIsolationVerified", "collectionIntegrityVerified", "accessRestricted", "cutoverNotPerformed"]) {
  if (evidence[key] !== true) throw new Error(`EAROS backup evidence failed: ${key} must be true`);
}
if (!Number.isInteger(evidence.retentionDays) || evidence.retentionDays < 1) {
  throw new Error("EAROS backup evidence failed: retentionDays must be a positive integer");
}
console.log("EAROS backup/restore evidence passed: encrypted backup, isolated restore, access restriction, collection integrity, and tenant isolation are recorded.");
