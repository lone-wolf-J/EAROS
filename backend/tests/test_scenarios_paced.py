"""Tests for the paced scenario runner and approval gate.

Verifies that:
- POST /api/scenarios/{id}/run returns an execution_id and initial state
- GET /api/scenarios/executions/{id}/state polls current progress
- The scenario reaches an awaiting_approval state
- POST /approve unblocks and the scenario completes
"""
from __future__ import annotations

import os
import time

import pytest
import requests


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"
RECRUITER_EMAIL = "demo.recruiter@levelshift.ai"


@pytest.fixture(scope="module")
def auth_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/dev-login", params={"email": RECRUITER_EMAIL})
    assert r.status_code == 200, r.text
    return s


class TestPacedScenario:
    def test_run_returns_execution_id(self, auth_session):
        r = auth_session.post(f"{BASE_URL}/api/scenarios/scn.java_chennai/run")
        assert r.status_code == 200, r.text
        d = r.json()
        assert "execution_id" in d
        assert d["status"] == "running"
        assert d["total_steps"] == 14
        assert d["current_step_idx"] == 0

    def test_full_paced_flow_with_approval(self, auth_session):
        r = auth_session.post(f"{BASE_URL}/api/scenarios/scn.sfdc_arch/run")
        assert r.status_code == 200
        exec_id = r.json()["execution_id"]

        # Poll for up to 40s waiting for approval gate
        seen_awaiting = False
        for _ in range(40):
            state = auth_session.get(
                f"{BASE_URL}/api/scenarios/executions/{exec_id}/state"
            ).json()
            if state["status"] == "awaiting_approval":
                seen_awaiting = True
                assert state["approval"] is not None
                assert "subject" in state["approval"]
                break
            if state["status"] in ("completed", "failed"):
                break
            time.sleep(1)
        assert seen_awaiting, "scenario never reached approval gate"

        # Approve it
        ap = auth_session.post(
            f"{BASE_URL}/api/scenarios/executions/{exec_id}/approve"
        )
        assert ap.status_code == 200
        assert ap.json()["decision"] == "approved"

        # Poll to completion
        for _ in range(15):
            state = auth_session.get(
                f"{BASE_URL}/api/scenarios/executions/{exec_id}/state"
            ).json()
            if state["status"] == "completed":
                assert state["progress_pct"] == 100
                assert state["result"]["approval_decision"] == "approved"
                return
            time.sleep(1)
        pytest.fail("scenario never completed after approval")

    def test_reject_flow(self, auth_session):
        r = auth_session.post(f"{BASE_URL}/api/scenarios/scn.dynamics_hyd/run")
        exec_id = r.json()["execution_id"]

        # wait for gate
        for _ in range(40):
            state = auth_session.get(
                f"{BASE_URL}/api/scenarios/executions/{exec_id}/state"
            ).json()
            if state["status"] == "awaiting_approval":
                break
            time.sleep(1)

        rj = auth_session.post(
            f"{BASE_URL}/api/scenarios/executions/{exec_id}/reject"
        )
        assert rj.status_code == 200
        assert rj.json()["decision"] == "rejected"

        for _ in range(15):
            state = auth_session.get(
                f"{BASE_URL}/api/scenarios/executions/{exec_id}/state"
            ).json()
            if state["status"] == "completed":
                assert state["result"]["approval_decision"] == "rejected"
                return
            time.sleep(1)
        pytest.fail("scenario never completed after rejection")

    def test_state_404(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/scenarios/executions/exe_bogus/state")
        assert r.status_code == 404

    def test_approve_without_gate_400(self, auth_session):
        # Start a fresh run and immediately try to approve — no gate yet
        r = auth_session.post(f"{BASE_URL}/api/scenarios/scn.ai_bang/run")
        exec_id = r.json()["execution_id"]
        ap = auth_session.post(
            f"{BASE_URL}/api/scenarios/executions/{exec_id}/approve"
        )
        assert ap.status_code == 400
