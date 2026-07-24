#!/usr/bin/env python3
"""Focused backend verification for Bug #3: /api/intake/analyze resilience."""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests


ROOT = Path("/app")
REPORT_DIR = ROOT / "test_reports"
REPORT_DIR.mkdir(exist_ok=True)
OUT = REPORT_DIR / "iteration_5_backend_results.json"
BRIEF = "Hiring a Salesforce Architect in Austin. Apex, LWC, CPQ. M4."


def read_frontend_api_url() -> str:
    env_path = ROOT / "frontend" / ".env"
    for line in env_path.read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not found")


def main() -> int:
    base_url = read_frontend_api_url()
    session = requests.Session()
    result = {
        "brief": BRIEF,
        "base_url": base_url,
        "checks": {},
        "pass": False,
    }

    try:
        login = session.post(
            f"{base_url}/api/auth/dev-login",
            params={"email": "demo.recruiter@levelshift.ai"},
            timeout=20,
        )
        result["login_status"] = login.status_code
        result["login_body_preview"] = login.text[:500]
        login.raise_for_status()

        started = time.monotonic()
        resp = session.post(
            f"{base_url}/api/intake/analyze",
            json={"brief": BRIEF},
            timeout=95,
        )
        elapsed = time.monotonic() - started
        result.update({
            "status_code": resp.status_code,
            "elapsed_seconds": round(elapsed, 2),
            "raw_body_preview": resp.text[:1000],
            "contains_cloudflare_raw": "cloudflare" in resp.text.lower()
            or "<html" in resp.text.lower()
            or "502 bad gateway" in resp.text.lower(),
        })

        if resp.headers.get("content-type", "").lower().startswith("application/json"):
            data = resp.json()
            intake = data.get("intake") or {}
            plan = data.get("sourcing_plan") or {}
            waves = plan.get("waves") or []
            result["parsed"] = {
                "intake_role_title": intake.get("role_title"),
                "intake_location": intake.get("location"),
                "intake_source": intake.get("source"),
                "matched_job_id": data.get("matched_job_id"),
                "sourcing_wave_count": len(waves),
                "must_have_skills": intake.get("must_have_skills"),
                "nice_to_have_skills": intake.get("nice_to_have_skills"),
            }
            result["checks"] = {
                "http_200": resp.status_code == 200,
                "within_90s": elapsed <= 90,
                "never_5xx": not (500 <= resp.status_code <= 599),
                "role_salesforce_architect": str(intake.get("role_title", "")).lower()
                == "salesforce architect",
                "location_austin": "austin" in str(intake.get("location", "")).lower(),
                "matched_seeded_job": data.get("matched_job_id") == "job_sfdc_arch_austin",
                "has_sourcing_wave": isinstance(waves, list) and len(waves) >= 1,
                "no_raw_cloudflare": not result["contains_cloudflare_raw"],
            }
            result["pass"] = all(result["checks"].values())
        else:
            result["checks"] = {
                "http_200": False,
                "json_response": False,
                "never_5xx": not (500 <= resp.status_code <= 599),
            }
    except Exception as exc:  # keep deterministic evidence even on timeout/failure
        result["exception"] = repr(exc)
        result["pass"] = False

    OUT.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())