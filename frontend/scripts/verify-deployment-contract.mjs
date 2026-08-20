import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const frontendRoot = resolve(import.meta.dirname, "..");
const repositoryRoot = resolve(frontendRoot, "..");

function read(relativePath) {
  return readFileSync(resolve(repositoryRoot, relativePath), "utf8");
}

function requireContract(condition, message) {
  if (!condition) throw new Error(`Deployment contract failed: ${message}`);
}

const packageJson = JSON.parse(readFileSync(resolve(frontendRoot, "package.json"), "utf8"));
const frontendDockerfile = read("frontend/Dockerfile");
const nginxConfiguration = read("frontend/nginx.conf");
const apiDockerfile = read("backend/Dockerfile");
const compose = read("docker-compose.production.yml");
const frontendConfiguration = read("docs/FRONTEND_CONFIGURATION.md");
const deploymentGuide = read("docs/DEPLOYMENT.md");

requireContract(packageJson.packageManager?.startsWith("yarn@1.22.22"), "frontend package manager must pin Yarn Classic 1.22.22");
requireContract(existsSync(resolve(frontendRoot, "yarn.lock")), "frontend yarn.lock must be committed");
requireContract(packageJson.scripts?.build === "vite build", "frontend production build must invoke Vite directly");
requireContract(frontendDockerfile.includes("yarn install --frozen-lockfile"), "frontend image must install exactly from yarn.lock");
requireContract(frontendDockerfile.includes("ARG VITE_BACKEND_URL"), "frontend image must accept the public API origin only as a build argument");
requireContract(frontendDockerfile.includes("NODE_ENV=production"), "frontend image must set production mode during build");
requireContract(!/COPY\s+.*\.env/i.test(frontendDockerfile), "frontend image must not copy environment files");
requireContract(nginxConfiguration.includes("listen 8080;") && nginxConfiguration.includes("location = /healthz"), "frontend proxy must expose a non-privileged health endpoint");
requireContract(nginxConfiguration.includes("Content-Security-Policy") && nginxConfiguration.includes("X-Frame-Options"), "frontend proxy must set baseline browser security headers");
requireContract(apiDockerfile.includes("USER earos") && apiDockerfile.includes("HEALTHCHECK"), "API image must use a non-root runtime user and health check");
requireContract(!/COPY\s+.*\.env/i.test(apiDockerfile), "API image must not copy environment files");
requireContract(compose.includes("EAROS_PUBLIC_API_ORIGIN") && compose.includes("condition: service_healthy"), "Compose must require an explicit public API origin and wait for API readiness");
requireContract(compose.includes("EAROS_ENV: production"), "Compose must force production API mode");
requireContract(frontendConfiguration.includes("VITE_BACKEND_URL") && frontendConfiguration.includes("HTTPS"), "frontend deployment documentation must require an HTTPS API origin");
requireContract(deploymentGuide.includes("CORS_ORIGINS") && deploymentGuide.includes("secret manager"), "deployment guidance must cover explicit CORS and secret-manager controls");

console.log("EAROS deployment contract passed: lockfile, build inputs, container safeguards, Compose readiness, and operator guidance are present.");
