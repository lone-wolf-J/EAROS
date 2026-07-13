"""
EAROS iteration-3 backend tests.
Covers: /api/deep-dive/executions, /api/deep-dive/replay/{cid},
scenario run correlation_id -> replay with >=5 of 6 lanes and 30+ messages,
approval + reflection events sharing correlation_id.
"""
import os
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

LANES = {"planner", "policy", "runtime", "capability", "world", "governance", "reflection"}


@pytest.fixture(scope="module")
def auth_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/dev-login", params={"email": RECRUITER_EMAIL})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def fresh_scenario_run(auth_session):
    r = auth_session.post(f"{BASE_URL}/api/scenarios/scn.ai_bang/run-sync", timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "correlation_id" in d
    return d


class TestDeepDiveList:
    def test_executions_returns_list(self, auth_session, fresh_scenario_run):
        r = auth_session.get(f"{BASE_URL}/api/deep-dive/executions", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1, "expected >=1 replayable execution"
        # each entry should have correlation_id
        first = data[0]
        assert "correlation_id" in first
        assert first.get("kind") in ("execution", "scenario")

    def test_fresh_scenario_in_list(self, auth_session, fresh_scenario_run):
        cid = fresh_scenario_run["correlation_id"]
        r = auth_session.get(f"{BASE_URL}/api/deep-dive/executions", timeout=15)
        data = r.json()
        cids = [e.get("correlation_id") for e in data]
        assert cid in cids, f"fresh scenario cid {cid} not in listed executions"


class TestDeepDiveReplay:
    def test_replay_ai_bang(self, auth_session, fresh_scenario_run):
        cid = fresh_scenario_run["correlation_id"]
        r = auth_session.get(f"{BASE_URL}/api/deep-dive/replay/{cid}", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        msgs = data.get("messages") or []
        assert len(msgs) >= 30, f"expected 30+ messages, got {len(msgs)}"
        lanes_hit = set()
        for m in msgs:
            lane = m.get("lane")
            if lane:
                lanes_hit.add(lane)
        # at least 5 of 6 active lanes (world may be missing)
        active = {"planner", "policy", "runtime", "capability", "governance", "reflection"}
        hit_active = lanes_hit & active
        assert len(hit_active) >= 5, f"expected >=5 active lanes, got {hit_active}"

    def test_rollup_present(self, auth_session, fresh_scenario_run):
        cid = fresh_scenario_run["correlation_id"]
        r = auth_session.get(f"{BASE_URL}/api/deep-dive/replay/{cid}", timeout=30)
        data = r.json()
        # roll-up keys – tolerant naming
        assert any(k in data for k in ("total_ms", "duration_ms", "total_latency_ms")), \
            f"no total_ms rollup: {list(data.keys())}"
        assert any(k in data for k in ("total_cost", "total_cost_usd", "cost_usd")), \
            f"no cost rollup: {list(data.keys())}"

    def test_replay_404_unknown_cid(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/deep-dive/replay/does-not-exist-xyz", timeout=10)
        assert r.status_code == 404

    def test_reflection_and_approval_events_share_cid(self, auth_session, fresh_scenario_run):
        cid = fresh_scenario_run["correlation_id"]
        r = auth_session.get(f"{BASE_URL}/api/deep-dive/replay/{cid}", timeout=30)
        data = r.json()
        msgs = data.get("messages") or []
        # scenario should have at least one reflection.created
        reflection_events = [m for m in msgs if "reflection" in (m.get("event_type") or m.get("type") or "").lower()]
        assert len(reflection_events) >= 1, "no reflection events found"
        # every message under this replay must share correlation_id
        for m in msgs:
            m_cid = m.get("correlation_id")
            if m_cid is not None:
                assert m_cid == cid, f"cross-cid leak: {m_cid} != {cid}"


class TestOfferPolicyInvariant:
    """Iteration-1 invariant: offer generation via cap.generate_offer -> awaiting_approval."""

    def test_offer_generation_awaits_approval(self, auth_session):
        payload = {
            "goal": "Generate offer for top candidate",
            "steps": [{
                "capability_id": "cap.generate_offer",
                "inputs": {"candidate_id": "cand_ai_staff_bang_00", "job_id": "job_ai_staff_bang"},
                "confidence": 0.9,
                "sensitivity": "restricted",
            }],
        }
        r = auth_session.post(f"{BASE_URL}/api/runtime/execute", json=payload, timeout=30)
        assert r.status_code in (200, 202), r.text
        d = r.json()
        status = (d.get("status") or "").lower()
        pending = d.get("pending_approvals") or []
        # policy must gate offer generation: any of the blocked/awaiting states, or a pending approval
        assert ("await" in status or "approval" in status or "block" in status or len(pending) >= 1), \
            f"offer generation did not gate on approval: status={status} pending={pending}"
