import { expect, test } from "@playwright/test";

const webBase = process.env.EAROS_BROWSER_WEB_BASE || "http://127.0.0.1:18080";
const apiBase = process.env.EAROS_BROWSER_API_BASE || webBase;
const screenshotDir = process.env.EAROS_BROWSER_SMOKE_OUTPUT || "/tmp/earos-infrastructure-browser-smoke";

const routes = [
  { path: "/ats", rootTestId: "ats-operations-root", image: "ats.png" },
  { path: "/ats/workflows", rootTestId: "ats-autonomy-root", image: "workflows.png" },
  { path: "/interview", rootTestId: "interview-suite-root", image: "interview.png" },
];

const coreAtsTabs = [
  { key: "candidates", image: "ats-candidates.png" },
  { key: "applications", image: "ats-applications.png" },
  { key: "interviews", image: "ats-interviews.png" },
  { key: "offers", image: "ats-offers.png" },
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
    await expect(page.getByTestId(route.rootTestId)).toBeVisible({ timeout: 30_000 });
    await page.screenshot({ path: `${screenshotDir}/${route.image}`, fullPage: true });
  }

  await page.goto(`${webBase}/ats`, { waitUntil: "domcontentloaded" });
  await expect(page.getByTestId("ats-operations-root")).toBeVisible({ timeout: 30_000 });
  for (const tab of coreAtsTabs) {
    await page.getByTestId(`ats-tab-${tab.key}`).click();
    await expect(page.getByTestId(`ats-workspace-${tab.key}`)).toBeVisible();
    await page.screenshot({ path: `${screenshotDir}/${tab.image}`, fullPage: true });
  }
});
