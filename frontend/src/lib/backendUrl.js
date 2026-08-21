export function resolveBackendUrl(value, { production = false, allowInsecureLocalhost = false } = {}) {
  const candidate = (value || "").trim();
  if (!candidate) {
    if (production) {
      throw new Error("VITE_BACKEND_URL must be set for an EAROS production client build.");
    }
    return "";
  }

  let parsed;
  try {
    parsed = new URL(candidate);
  } catch {
    throw new Error("VITE_BACKEND_URL must be an absolute HTTP(S) origin.");
  }

  if (!["http:", "https:"].includes(parsed.protocol) || !parsed.hostname) {
    throw new Error("VITE_BACKEND_URL must be an absolute HTTP(S) origin.");
  }
  if (parsed.username || parsed.password) {
    throw new Error("VITE_BACKEND_URL must not contain credentials.");
  }
  if (parsed.pathname !== "/" || parsed.search || parsed.hash) {
    throw new Error("VITE_BACKEND_URL must be an origin only; paths, queries, and fragments are not permitted.");
  }
  const isLoopback = ["127.0.0.1", "localhost", "::1"].includes(parsed.hostname);
  if (production && parsed.protocol !== "https:" && !(allowInsecureLocalhost && isLoopback)) {
    throw new Error("VITE_BACKEND_URL must use HTTPS for an EAROS production client build.");
  }

  return parsed.origin;
}
