"""Focused UI verification for Bug #3.

Run with the provided Playwright browser harness. Verifies that /intake completes
the Salesforce Architect Austin happy path, renders the handoff CTA, and does
not show raw 502/Cloudflare gateway error text in the user-visible DOM.
"""

async def run(page):
    await page.set_viewport_size({"width": 1920, "height": 1080})
    responses = []

    def on_response(resp):
        if "/api/intake/analyze" in resp.url:
            responses.append({"url": resp.url, "status": resp.status})

    page.on("response", on_response)
    await page.goto("https://hiring-runtime.preview.emergentagent.com/intake")
    await page.wait_for_load_state("domcontentloaded")

    demo_btn = page.get_by_test_id("demo-login-recruiter-btn")
    if await demo_btn.count() > 0 and await demo_btn.first.is_visible():
        await demo_btn.first.click(force=True)
        await page.wait_for_load_state("networkidle")
        await page.goto("https://hiring-runtime.preview.emergentagent.com/intake")
        await page.wait_for_load_state("domcontentloaded")

    await page.wait_for_selector('[data-testid="intake-root"]', timeout=30000)
    await page.fill(
        '[data-testid="intake-brief-input"]',
        "Hiring a Salesforce Architect in Austin. Apex, LWC, CPQ. M4.",
    )
    await page.click('[data-testid="intake-run-btn"]', force=True)
    await page.wait_for_selector(
        '[data-testid="job-arch-handoff-btn"]', state="visible", timeout=90000,
    )

    body_text = await page.locator("body").inner_text(timeout=5000)
    body_html = await page.locator("body").inner_html(timeout=5000)
    combined = (body_text + body_html).lower()
    raw_gateway_leak = any(
        token in combined
        for token in ["502 bad gateway", "error code: 502", "cloudflare ray id", "bad gateway"]
    )

    assert responses and all(r["status"] == 200 for r in responses), responses
    assert await page.locator('[data-testid="job-arch-handoff-btn"]').is_enabled()
    assert "job_sfdc_arch_austin" in body_text
    assert "Salesforce Architect" in body_text
    assert "Austin" in body_text
    assert not raw_gateway_leak