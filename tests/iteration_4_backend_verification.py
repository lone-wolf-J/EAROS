"""Focused backend verification for bug pass iteration 4.

Tests only the user-reported issues:
- scenario approval gate pause and completion outputs
- candidate fit scores and duplicated title data
- intake endpoint happy path response shape
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import requests


BASE_URL = os.environ.get(
    "API_BASE_URL",
    "https://hiring-runtime.preview.emergentagent.com",
).rstrip("/")
API = f"{BASE_URL}/api"
OUT_PATH = Path("/app/test_reports/iteration_4_backend_results.json")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def get_session() -> requests.Session:
    s = requests.Session()
    r = s.post(f"{API}/auth/dev-login?email=demo.recruiter%40levelshift.ai", timeout=30)
    r.raise_for_status()
    return s


def poll_state(session: requests.Session, exec_id: str) -> dict:
    r = session.get(f"{API}/scenarios/executions/{exec_id}/state", timeout=30)
    r.raise_for_status()
    return r.json()


def run_scenario_gate_and_counts(session: requests.Session) -> dict:
    started = session.post(f"{API}/scenarios/scn.sfdc_arch/run", timeout=30)
    started.raise_for_status()
    exec_id = started.json()["execution_id"]

    awaiting_state = None
    deadline = time.time() + 80
    samples = []
    while time.time() < deadline:
        state = poll_state(session, exec_id)
        samples.append({
            "t": round(time.time(), 1),
            "status": state.get("status"),
            "idx": state.get("current_step_idx"),
            "label": (state.get("steps") or [{}])[state.get("current_step_idx", 0)].get("label")
            if state.get("steps") else None,
            "remaining": (state.get("approval") or {}).get("seconds_remaining"),
        })
        if state.get("status") == "awaiting_approval":
            awaiting_state = state
            break
        if state.get("status") in {"completed", "failed", "cancelled"}:
            break
        time.sleep(1)

    assert_true(awaiting_state is not None, f"scenario never reached awaiting_approval; samples={samples[-5:]}")
    assert_true(awaiting_state["steps"][awaiting_state["current_step_idx"]]["key"] == "approval", "awaiting state not on approval step")
    remaining = (awaiting_state.get("approval") or {}).get("seconds_remaining")
    assert_true(remaining is not None and remaining > 540, f"approval countdown not near 600s: {remaining}")

    hold_samples = []
    hold_started = time.time()
    while time.time() - hold_started < 8.5:
        state = poll_state(session, exec_id)
        hold_samples.append({"elapsed": round(time.time() - hold_started, 1), "status": state.get("status"), "remaining": (state.get("approval") or {}).get("seconds_remaining")})
        assert_true(state.get("status") == "awaiting_approval", f"scenario did not hold awaiting approval: {hold_samples}")
        text_blob = json.dumps(state)
        assert_true("auto_approved" not in text_blob, "auto_approved appeared before explicit approval")
        time.sleep(1)

    approval_resp = session.post(f"{API}/scenarios/executions/{exec_id}/approve", timeout=30)
    approval_resp.raise_for_status()
    assert_true(approval_resp.json().get("decision") == "approved", "approve endpoint did not return approved")

    final = None
    deadline = time.time() + 45
    while time.time() < deadline:
        state = poll_state(session, exec_id)
        if state.get("status") == "completed":
            final = state
            break
        if state.get("status") in {"failed", "cancelled"}:
            raise AssertionError(f"scenario ended {state.get('status')}: {state}")
        time.sleep(1)

    assert_true(final is not None, "scenario did not complete after approval")
    assert_true(final.get("result", {}).get("approval_decision") == "approved", f"wrong approval decision: {final.get('result')}")
    assert_true("auto_approved" not in json.dumps(final), "auto_approved appeared in final state")

    outputs = {step["key"]: step.get("output") or "" for step in final.get("steps", [])}
    sourced = re.search(r"Sourced (\d+) candidates", outputs.get("sourcing", ""))
    parsed = re.search(r"Parsed (\d+) resumes", outputs.get("resume_intel", ""))
    outreach = re.search(r"Drafted personalised outreach for top (\d+) candidates", outputs.get("outreach", ""))
    screened = re.search(r"Screened (\d+) candidates\. (\d+) advanced", outputs.get("screening", ""))
    assert_true(sourced and int(sourced.group(1)) > 0, f"bad sourcing output: {outputs.get('sourcing')}")
    assert_true(parsed and int(parsed.group(1)) > 0, f"bad resume output: {outputs.get('resume_intel')}")
    assert_true(outreach and int(outreach.group(1)) > 0, f"bad outreach output: {outputs.get('outreach')}")
    assert_true(screened and int(screened.group(1)) > 0 and int(screened.group(2)) <= int(screened.group(1)), f"bad screening output: {outputs.get('screening')}")

    return {
        "execution_id": exec_id,
        "awaiting_remaining_seconds": remaining,
        "hold_samples": hold_samples,
        "outputs": {k: outputs[k] for k in ["sourcing", "resume_intel", "outreach", "screening", "approval"]},
        "result": final.get("result"),
    }


def verify_candidates(session: requests.Session) -> dict:
    r = session.get(f"{API}/world/candidates", timeout=30)
    r.raise_for_status()
    candidates = r.json()
    assert_true(len(candidates) > 0, "no candidates returned")
    fit_scores = [c.get("fit_score", 0) for c in candidates]
    assert_true(all(isinstance(x, (int, float)) and x > 0 for x in fit_scores), "some candidates have missing/zero fit_score")
    bad_titles = [c for c in candidates if re.search(r"senior\s+senior|sr\.\s*sr\.", c.get("current_title", ""), re.I)]
    assert_true(not bad_titles, f"duplicated seniority titles remain: {bad_titles[:5]}")
    return {
        "count": len(candidates),
        "fit_min": min(fit_scores),
        "fit_max": max(fit_scores),
        "fit_avg": sum(fit_scores) / len(fit_scores),
        "duplicate_senior_titles": len(bad_titles),
    }


def verify_intake_happy_path(session: requests.Session) -> dict:
    brief = "Hiring a Salesforce Architect in Austin. Apex, LWC, CPQ. Anchor architect for the Americas book. M4 level."
    r = session.post(f"{API}/intake/analyze", json={"brief": brief}, timeout=120)
    r.raise_for_status()
    data = r.json()
    assert_true(data.get("intake"), "intake missing")
    assert_true(data.get("matched_job_id"), "matched_job_id missing")
    assert_true(data.get("sourcing_plan"), "sourcing_plan missing")
    return {
        "matched_job_id": data.get("matched_job_id"),
        "role_title": data.get("intake", {}).get("role_title"),
        "source": data.get("intake", {}).get("source"),
    }


def main() -> int:
    results = {"base_url": BASE_URL, "checks": {}, "failures": []}
    session = get_session()
    checks = [
        ("scenario_gate_and_counts", lambda: run_scenario_gate_and_counts(session)),
        ("candidates_fit_and_titles", lambda: verify_candidates(session)),
        ("intake_happy_path", lambda: verify_intake_happy_path(session)),
    ]
    for name, fn in checks:
        try:
            results["checks"][name] = {"status": "passed", "evidence": fn()}
            print(f"PASS {name}")
        except Exception as exc:  # noqa: BLE001
            results["checks"][name] = {"status": "failed", "error": str(exc)}
            results["failures"].append({"check": name, "error": str(exc)})
            print(f"FAIL {name}: {exc}")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 1 if results["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())