"""Focused Playwright steps for bug pass iteration 4.

This file mirrors the script executed by the browser automation tool and covers:
- scenario approval UI label/countdown and explicit approval
- intake happy path and graceful error fallback elements/source behavior
- recruiter avg fit strip
- world tab switching
"""

SCRIPT = r'''
try:
    await page.set_viewport_size({"width": 1920, "height": 1080})
    await page.goto("https://hiring-runtime.preview.emergentagent.com", wait_until="domcontentloaded")
    await page.get_by_test_id("demo-login-recruiter-btn").click()
    await page.wait_for_url("**/dashboard", timeout=30000)
    print("PASS login")

    # Bug 4: recruiter Avg fit must be >0
    await page.goto("https://hiring-runtime.preview.emergentagent.com/recruiter", wait_until="domcontentloaded")
    await page.wait_for_selector('[data-testid="pipeline-intel"]', timeout=30000)
    intel = await page.get_by_test_id("pipeline-intel").inner_text()
    print(f"pipeline intel: {intel}")
    import re
    m = re.search(r"AVG FIT\s*\n\s*(\d+)%", intel, re.I)
    assert m and int(m.group(1)) > 0, f"Avg fit not >0 in strip: {intel}"
    print("PASS recruiter avg fit >0")

    # Bug 5: world tabs switch away from Jobs table
    await page.goto("https://hiring-runtime.preview.emergentagent.com/world", wait_until="domcontentloaded")
    await page.wait_for_selector('[data-testid="world-state-root"]', timeout=30000)
    tab_expectations = [
        ("world-tab-org", "ORGANIZATION", "TITLE"),
        ("world-tab-departments", "LEADER", "TITLE"),
        ("world-tab-teams", "MANAGER", "TITLE"),
        ("world-tab-candidates", "NAME", "SALARY BAND"),
        ("world-tab-offers", "CANDIDATE", "TITLE"),
        ("world-tab-skills", "MARKET SCARCITY", "TITLE"),
    ]
    for testid, expected, not_expected in tab_expectations:
        await page.get_by_test_id(testid).click()
        await page.wait_for_timeout(500)
        txt = await page.get_by_test_id("world-state-root").inner_text()
        assert expected in txt, f"{testid} did not show expected content {expected}"
        if testid != "world-tab-candidates":
            # The reported bug was all tabs keeping the Jobs salary/title table visible.
            assert "SALARY BAND" not in txt, f"{testid} still appears to show Jobs table"
        print(f"PASS world tab {testid}")

    # Bug 3: source-visible retry/friendly UI elements + happy path handoff
    await page.goto("https://hiring-runtime.preview.emergentagent.com/intake", wait_until="domcontentloaded")
    await page.wait_for_selector('[data-testid="intake-root"]', timeout=30000)
    await page.get_by_test_id("intake-brief-input").fill("Hiring a Salesforce Architect in Austin. Apex, LWC, CPQ. Anchor architect for the Americas book. M4 level.")
    await page.get_by_test_id("intake-run-btn").click()
    await page.wait_for_selector('[data-testid="job-arch-handoff-btn"]', timeout=120000)
    assert await page.get_by_test_id("job-arch-handoff-btn").is_visible(), "handoff button not visible"
    body = await page.locator("body").inner_text()
    assert "Cloudflare" not in body and "<html" not in body.lower(), "raw Cloudflare/HTML leaked in intake UI"
    print("PASS intake happy path handoff and no raw Cloudflare text")

    # Bug 1 UI smoke: run scenario until approval card appears, verify label/countdown, approve to complete.
    await page.goto("https://hiring-runtime.preview.emergentagent.com/scenarios", wait_until="domcontentloaded")
    await page.wait_for_selector('[data-testid="scenarios-root"]', timeout=30000)
    await page.get_by_test_id("scenario-run-scn.sfdc_arch").click()
    await page.wait_for_selector('[data-testid="scenario-approval-gate"]', timeout=90000)
    gate_text = await page.get_by_test_id("scenario-approval-gate").inner_text()
    countdown = await page.get_by_test_id("scenario-approval-countdown").inner_text()
    print(f"approval gate text: {gate_text}; countdown={countdown}")
    assert "SCENARIO CANCELS IN" in gate_text, "approval gate does not show cancel countdown label"
    assert "AUTO-RESUME" not in gate_text and "auto_approved" not in gate_text, "auto-resume/auto_approved shown in approval gate"
    assert ":" in countdown, f"countdown not minute-style near 10 minutes: {countdown}"
    await page.wait_for_timeout(3000)
    assert await page.get_by_test_id("scenario-approval-gate").is_visible(), "approval gate disappeared without click"
    await page.get_by_test_id("scenario-approve-btn").click()
    await page.wait_for_selector('text=SCENARIO COMPLETE', timeout=60000)
    complete_text = await page.get_by_test_id("scenario-live-panel").inner_text()
    assert "auto_approved" not in complete_text, "auto_approved appeared after approval"
    print("PASS scenario approval UI explicit approval")

    # Get error messages using specific selectors
    error_text = await page.evaluate("""() => {
    const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
    return errorElements.map(el => el.textContent).join(", ");
    }""")
    if error_text:
        print(f"Found error message: {error_text}")
    else:
        print("No error messages found on the page")
except Exception as e:
    print(f"FAIL UI verification: {e}")
    raise
'''