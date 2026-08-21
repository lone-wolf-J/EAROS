import { describe, expect, it } from "vitest";
import { resolveBackendUrl } from "./backendUrl.js";

describe("EAROS backend origin validation", () => {
  it("requires HTTPS in ordinary production builds", () => {
    expect(() => resolveBackendUrl("http://api.example.invalid", { production: true })).toThrow(/must use HTTPS/);
    expect(resolveBackendUrl("https://api.example.invalid", { production: true })).toBe("https://api.example.invalid");
  });

  it("permits HTTP only for an explicitly enabled loopback smoke origin", () => {
    expect(
      resolveBackendUrl("http://127.0.0.1:18000", {
        production: true,
        allowInsecureLocalhost: true,
      }),
    ).toBe("http://127.0.0.1:18000");
    expect(() =>
      resolveBackendUrl("http://staging.example.invalid", {
        production: true,
        allowInsecureLocalhost: true,
      }),
    ).toThrow(/must use HTTPS/);
  });
});
