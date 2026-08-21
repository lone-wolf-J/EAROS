import { expect, test } from "@playwright/test";

const webBase = process.env.EAROS_BROWSER_WEB_BASE || "http://127.0.0.1:18080";
const apiBase = process.env.EAROS_BROWSER_API_BASE || webBase;
const screenshotDir = process.env.EAROS_BROWSER_SMOKE_OUTPUT || "/tmp/earos-infrastructure-browser-smoke";

const routes = [
  { path: "/ats", marker: "Requisitions", image: "ats.png" },
  { path: "/ats/workflows", marker: "Source consented prospects", image: "workflows.png" },
  { path: "/interview", marker: "AI Screening", image: "interview.png" },
];

test("synthetic recruiter can load compiled protected recruiter workflows", async ({ page, context }) => {
  await page.goto(`${webBase}/`, { waitUntil: "domcontentloaded" });
  const loginStatus = await page.evaluate(async () => {
    const response = await fetch("/api/auth/dev-login?email=demo.recruiter%40levelshift.ai", {
      method: "POST",
      credentials: "include",
    });
    return response.status;
  });

  expect(loginStatus).toBe(200);
  await expect.poll(async () => (await context.cookies(apiBase)).some((cookie) => cookie.name === "session_token")).toBe(true);
  await page.reload({ waitUntil: "domcontentloaded" });

  for (const route of routes) {
    await page.goto(`${webBase}${route.path}`, { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(new RegExp(`${route.path.replaceAll("/", "\\/")}$`));
    await expect(page.locator("body")).toContainText(route.marker, { timeout: 30_000 });
    await page.screenshot({ path: `${screenshotDir}/${route.image}`, fullPage: true });
  }
});
