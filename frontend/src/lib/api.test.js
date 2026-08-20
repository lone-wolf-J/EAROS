import { describe, expect, it } from "vitest";
import { resolveBackendUrl } from "./backendUrl";

describe("resolveBackendUrl", () => {
  it("accepts an origin and normalizes a trailing slash", () => {
    expect(resolveBackendUrl("https://api.earos.example/")).toBe("https://api.earos.example");
  });

  it("allows an empty value only outside a production build", () => {
    expect(resolveBackendUrl("")).toBe("");
    expect(() => resolveBackendUrl("", { production: true })).toThrow("must be set");
  });

  it("rejects malformed, credential-bearing, and path-bearing API values", () => {
    expect(() => resolveBackendUrl("not-a-url", { production: true })).toThrow("absolute HTTP(S) origin");
    expect(() => resolveBackendUrl("https://user:pass@api.earos.example", { production: true })).toThrow("credentials");
    expect(() => resolveBackendUrl("https://api.earos.example/internal", { production: true })).toThrow("origin only");
  });

  it("requires HTTPS for production configuration", () => {
    expect(() => resolveBackendUrl("http://api.earos.example", { production: true })).toThrow("HTTPS");
  });
});
