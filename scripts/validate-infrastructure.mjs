import { readFileSync } from "node:fs";

const args = new Set(process.argv.slice(2));
const envFileIndex = process.argv.indexOf("--env-file");

function fail(message) {
  throw new Error(`EAROS infrastructure validation failed: ${message}`);
}

function loadEnvFile(filePath) {
  for (const rawLine of readFileSync(filePath, "utf8").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const separator = line.indexOf("=");
    if (separator < 1) fail(`invalid environment line in ${filePath}`);
    const key = line.slice(0, separator).trim();
    const rawValue = line.slice(separator + 1).trim();
    const value = rawValue.replace(/^(['"])(.*)\1$/, "$2");
    if (!process.env[key]) process.env[key] = value;
  }
}

if (envFileIndex >= 0) {
  const envFile = process.argv[envFileIndex + 1];
  if (!envFile || envFile.startsWith("--")) fail("--env-file requires a readable path");
  loadEnvFile(envFile);
}

const runtimeMode = args.has("--runtime");
const validationMode = process.env.EAROS_VALIDATION_MODE || "staging";
const isComposeLocal = validationMode === "compose-local";

function required(name) {
  const value = process.env[name]?.trim();
  if (!value || /replace[-_ ]with|^replace[-_ ]|example\.invalid/i.test(value)) {
    fail(`${name} must be supplied through the controlled validation environment`);
  }
  return value;
}

function origin(name, allowHttpLocalhost = false) {
  const value = required(name);
  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    fail(`${name} must be an absolute origin`);
  }
  const localHttp = allowHttpLocalhost && parsed.protocol === "http:" && ["127.0.0.1", "localhost"].includes(parsed.hostname);
  if ((parsed.protocol !== "https:" && !localHttp) || parsed.username || parsed.password || parsed.pathname !== "/" || parsed.search || parsed.hash) {
    fail(`${name} must be a bare ${allowHttpLocalhost ? "HTTPS or local HTTP" : "HTTPS"} origin without credentials, path, query, or fragment`);
  }
  return parsed.origin;
}

const apiOrigin = origin("EAROS_PUBLIC_API_ORIGIN", isComposeLocal);
const webOrigin = origin("EAROS_STAGING_WEB_ORIGIN", isComposeLocal);
const allowedOrganizationId = required("EAROS_SMOKE_ALLOWED_ORGANIZATION_ID");
const crossTenantCandidateId = required("EAROS_SMOKE_CROSS_TENANT_CANDIDATE_ID");

if (process.env.EAROS_SMOKE_AUTH_TOKEN?.includes("replace")) fail("EAROS_SMOKE_AUTH_TOKEN must not be a placeholder");
if (/demobackend\.emergentagent\.com/i.test(process.env.AUTH_SESSION_DATA_URL || "")) {
  fail("AUTH_SESSION_DATA_URL must never use the inherited demonstration identity service");
}

console.log(`EAROS infrastructure preflight passed for ${validationMode}: controlled origins, tenant identifiers, and fail-closed identity boundary are present.`);

if (!runtimeMode) process.exit(0);

const authToken = required("EAROS_SMOKE_AUTH_TOKEN");
const authHeaders = { Authorization: `Bearer ${authToken}`, Accept: "application/json" };

async function request(originValue, path, { headers = {}, expected = [200], expectJson = false } = {}) {
  const response = await fetch(`${originValue}${path}`, { headers });
  if (!expected.includes(response.status)) {
    const body = (await response.text()).slice(0, 500);
    fail(`${path} returned HTTP ${response.status}; expected ${expected.join(" or ")}; response: ${body}`);
  }
  const body = expectJson ? await response.json() : await response.text();
  return { response, body };
}

const { body: health } = await request(apiOrigin, "/api/health", { expectJson: true });
if (health?.ok !== true || health?.kind !== "liveness") fail("/api/health must report liveness ok");

const { body: ready } = await request(apiOrigin, "/api/ready", { expectJson: true });
if (ready?.ok !== true || ready?.kind !== "readiness") fail("/api/ready must report readiness ok");

const { body: proxyHealth } = await request(webOrigin, "/healthz");
if (!/ok/i.test(proxyHealth)) fail("frontend /healthz must return ok");

for (const route of ["/", "/ats", "/ats/workflows", "/enterprise-controls"]) {
  const { body } = await request(webOrigin, route);
  if (!/id=["']root["']/.test(body)) fail(`${route} did not return the EAROS SPA shell`);
}

const { body: identity } = await request(apiOrigin, "/api/auth/me", { headers: authHeaders, expectJson: true });
const organizationId = identity?.organization_id ?? identity?.organizationId ?? identity?.organization?.id;
if (organizationId !== allowedOrganizationId) fail("authenticated smoke identity did not resolve to EAROS_SMOKE_ALLOWED_ORGANIZATION_ID");

for (const route of ["/api/world/organization", "/api/ats/requisitions", "/api/ats/candidates", "/api/ats/pipelines", "/api/ats/offers", "/api/ats/interviews"]) {
  await request(apiOrigin, route, { headers: authHeaders, expectJson: true });
}

await request(apiOrigin, `/api/world/candidates/${encodeURIComponent(crossTenantCandidateId)}`, { headers: authHeaders, expected: [403, 404], expectJson: true });

console.log("EAROS infrastructure runtime validation passed: liveness, readiness, proxy health, SPA shell, authenticated recruiting reads, and cross-tenant candidate denial are verified.");
