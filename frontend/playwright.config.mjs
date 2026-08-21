import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  timeout: 45_000,
  retries: 0,
  reporter: [["line"]],
  use: {
    browserName: "chromium",
    headless: true,
    screenshot: "only-on-failure",
  },
});
