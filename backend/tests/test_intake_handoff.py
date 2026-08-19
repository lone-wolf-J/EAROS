"""Tests for the Task 2 Job Architecture handoff: intake now returns
matched_job_id and a structured sourcing_plan.
"""
from __future__ import annotations

import os
import pytest
import requests

BASE_URL = (os.environ.get("EAROS_TEST_BACKEND_URL") or os.environ.get("VITE_BACKEND_URL") or "").rstrip("/")
pytestmark = pytest.mark.skipif(
    not BASE_URL,
    reason="Live EAROS API tests require EAROS_TEST_BACKEND_URL (or VITE_BACKEND_URL) and a seeded test environment.",
)


@pytest.fixture(scope="module")
def s():
    session = requests.Session()
    r = session.post(
        f"{BASE_URL}/api/auth/dev-login",
        params={"email": "demo.recruiter@levelshift.ai"},
    )
    assert r.status_code == 200
    return session


def _analyze(session, brief):
    r = session.post(f"{BASE_URL}/api/intake/analyze", json={"brief": brief}, timeout=120)
    assert r.status_code == 200, r.text
    return r.json()


class TestIntakeHandoff:
    def test_returns_sourcing_plan_and_match(self, s):
        d = _analyze(s, "Hiring a Salesforce Architect in Austin. Apex, LWC, CPQ. M4.")
        assert "intake" in d
        assert "sourcing_plan" in d
        assert "matched_job_id" in d
        assert d["matched_job_id"] == "job_sfdc_arch_austin"

        # Sourcing plan shape (reuse the same response — one LLM call per suite)
        plan = d["sourcing_plan"]
        assert isinstance(plan["waves"], list)
        assert len(plan["waves"]) >= 1
        for w in plan["waves"]:
            assert "wave" in w
            assert "channels" in w
            assert w["target_candidates"] > 0
        assert plan["estimated_reach_candidates"] > 0
        assert plan["estimated_sweep_minutes"] > 0
        assert isinstance(plan["search_string"], str)

    def test_no_match_still_returns_plan(self, s):
        # Deliberately vague/unrelated brief
        d = _analyze(s, "We need someone for miscellaneous administrative work.")
        # Whether or not it matches, plan and intake must exist
        assert "sourcing_plan" in d
        assert d["sourcing_plan"]["waves"]
