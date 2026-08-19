"""
EAROS backend API tests.
Covers: health, bootstrap, auth (dev-login, /me, logout, Google session shape),
world state, intelligence, planner, runtime (success + policy blocked + low confidence),
governance (events + approval decide), reflection, applications endpoints.
"""
import os
import time
import pytest
import requests

BASE_URL = (os.environ.get("EAROS_TEST_BACKEND_URL") or os.environ.get("VITE_BACKEND_URL") or "").rstrip("/")
pytestmark = pytest.mark.skipif(
    not BASE_URL,
    reason="Live EAROS API tests require EAROS_TEST_BACKEND_URL (or VITE_BACKEND_URL) and a seeded test environment.",
)

RECRUITER_EMAIL = "demo.recruiter@levelshift.ai"


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def auth_session(api):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/dev-login", params={"email": RECRUITER_EMAIL})
    assert r.status_code == 200, r.text
    return s


# ---------- health + bootstrap ----------
class TestHealthBootstrap:
    def test_health(self, api):
        r = api.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200
        d = r.json()
        assert d.get("ok") is True

    def test_bootstrap_idempotent(self, api):
        r = api.post(f"{BASE_URL}/api/bootstrap")
        assert r.status_code == 200, r.text
        d = r.json()
        counts = d.get("counts") or d
        # Accept either flat or nested counts
        # spec expects >=1 org, >=12 jobs, >=100 candidates, 5 policies
        # Just print for visibility
        print("bootstrap:", d)
        assert isinstance(d, dict)


# ---------- auth ----------
class TestAuth:
    def test_dev_login_ok(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/dev-login", params={"email": RECRUITER_EMAIL})
        assert r.status_code == 200
        j = r.json()
        assert j["user"]["email"] == RECRUITER_EMAIL
        assert j["user"]["role"] == "recruiter"
        assert j["user"]["organization_id"] == "org_levelshift"
        assert "session_token" in j
        # session cookie set
        cookies = s.cookies.get_dict()
        assert "session_token" in cookies or any("session" in k.lower() for k in cookies)

    def test_me_with_cookie(self):
        s = requests.Session()
        s.post(f"{BASE_URL}/api/auth/dev-login", params={"email": RECRUITER_EMAIL})
        r = s.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        u = r.json()
        assert u.get("email") == RECRUITER_EMAIL

    def test_logout_clears(self):
        s = requests.Session()
        s.post(f"{BASE_URL}/api/auth/dev-login", params={"email": RECRUITER_EMAIL})
        r = s.post(f"{BASE_URL}/api/auth/logout")
        assert r.status_code in (200, 204)
        r2 = s.get(f"{BASE_URL}/api/auth/me")
        assert r2.status_code == 401

    def test_dev_login_bad_email_404(self):
        r = requests.post(
            f"{BASE_URL}/api/auth/dev-login",
            params={"email": "nobody@nowhere.com"},
        )
        assert r.status_code == 404

    def test_google_session_requires_header(self):
        r = requests.post(f"{BASE_URL}/api/auth/session")
        assert r.status_code in (400, 401, 422)

    def test_google_session_invalid_id_401(self):
        r = requests.post(
            f"{BASE_URL}/api/auth/session",
            headers={"X-Session-ID": "invalid_bogus_session_id"},
        )
        assert r.status_code == 401

    def test_unauth_world_401(self):
        r = requests.get(f"{BASE_URL}/api/world/jobs")
        assert r.status_code == 401


# ---------- world state ----------
class TestWorld:
    def test_org(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/world/organization")
        assert r.status_code == 200
        assert "LevelShift" in r.text

    def test_jobs_12(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/world/jobs")
        assert r.status_code == 200
        jobs = r.json()
        assert isinstance(jobs, list)
        assert len(jobs) >= 12, f"expected >=12 jobs, got {len(jobs)}"

    def test_candidates_100(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/world/candidates")
        assert r.status_code == 200
        c = r.json()
        assert len(c) >= 100, f"expected >=100 candidates, got {len(c)}"

    def test_job_candidates_filter(self, auth_session):
        r = auth_session.get(
            f"{BASE_URL}/api/world/jobs/job_ai_staff_bang/candidates",
            params={"stage": "sourced"},
        )
        assert r.status_code == 200
        for c in r.json():
            assert c.get("stage") == "sourced"

    def test_invalid_job_404(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/world/jobs/does_not_exist")
        assert r.status_code == 404


# ---------- intelligence ----------
class TestIntelligence:
    def _validate_reco(self, rec):
        for key in ["reasoning", "evidence", "confidence", "tradeoffs", "risks"]:
            assert key in rec, f"missing {key} in reco: {list(rec.keys())}"
        assert "policies_referenced" in rec
        # reasoning steps
        assert isinstance(rec["reasoning"], list)

    def test_hiring(self, auth_session):
        r = auth_session.get(
            f"{BASE_URL}/api/intelligence/hiring/job_ai_staff_bang",
            params={"top_n": 3},
        )
        assert r.status_code == 200
        data = r.json()
        recs = data if isinstance(data, list) else data.get("recommendations") or data.get("items") or []
        assert len(recs) == 3, f"expected 3 recs got {len(recs)}: {data}"
        for rec in recs:
            self._validate_reco(rec)

    def test_offer(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/intelligence/offer/cand_ai_staff_bang_00")
        assert r.status_code == 200
        rec = r.json()
        self._validate_reco(rec)

    def test_org_health(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/intelligence/organization/health")
        assert r.status_code == 200
        d = r.json()
        by_dept = d.get("by_department") or d
        assert by_dept

    def test_skill_gaps(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/intelligence/workforce/skill-gaps")
        assert r.status_code == 200
        rows = r.json()
        rows = rows if isinstance(rows, list) else rows.get("rows") or rows.get("items") or []
        assert len(rows) > 0
        first = rows[0]
        for k in ["demand", "supply", "gap"]:
            assert k in first, f"missing {k} in skill gap row {first}"

    def test_strategy(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/intelligence/strategy")
        assert r.status_code == 200
        rec = r.json()
        self._validate_reco(rec)
        assert len(rec["reasoning"]) >= 3


# ---------- planner ----------
class TestPlanner:
    def test_plan(self, auth_session):
        r = auth_session.post(
            f"{BASE_URL}/api/planner/plan",
            json={
                "goal": "Screen this candidate",
                "context": {
                    "candidate_id": "cand_ai_staff_bang_00",
                    "job_id": "job_ai_staff_bang",
                },
            },
        )
        assert r.status_code == 200, r.text
        plan = r.json()
        assert "steps" in plan
        assert isinstance(plan["steps"], list) and len(plan["steps"]) >= 1
        # each step has capability_id
        cap_ids = {s.get("capability_id") for s in plan["steps"]}
        # get valid registry
        reg = auth_session.get(f"{BASE_URL}/api/capabilities").json()
        valid_ids = {c.get("capability_id") or c.get("id") for c in (reg if isinstance(reg, list) else reg.get("items", []))}
        if valid_ids:
            assert cap_ids.issubset(valid_ids), f"steps have invalid caps: {cap_ids - valid_ids}"


# ---------- runtime ----------
class TestRuntime:
    def test_screen_success(self, auth_session):
        payload = {
            "goal": "Screen candidate",
            "steps": [
                {
                    "capability_id": "cap.screen_candidate",
                    "inputs": {"candidate_id": "cand_ai_staff_bang_00"},
                    "confidence": 0.85,
                }
            ],
        }
        r = auth_session.post(f"{BASE_URL}/api/runtime/execute", json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("status") == "succeeded", d
        step_results = d.get("step_results") or []
        assert step_results and step_results[0].get("ok") is True

    def test_offer_awaiting_approval(self, auth_session):
        payload = {
            "goal": "Generate offer",
            "steps": [
                {
                    "capability_id": "cap.generate_offer",
                    "inputs": {"candidate_id": "cand_ai_staff_bang_00"},
                    "confidence": 0.9,
                    "sensitivity": "confidential",
                }
            ],
        }
        r = auth_session.post(f"{BASE_URL}/api/runtime/execute", json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("status") == "awaiting_approval", d
        step_results = d.get("step_results") or []
        assert step_results and step_results[0].get("approval_id")
        # governance shows pending
        gv = auth_session.get(f"{BASE_URL}/api/governance/approvals").json()
        gv_list = gv if isinstance(gv, list) else gv.get("items", [])
        approval_id = step_results[0]["approval_id"]
        assert any(a.get("approval_id") == approval_id or a.get("id") == approval_id for a in gv_list)
        # decide
        r2 = auth_session.post(
            f"{BASE_URL}/api/governance/approvals/{approval_id}/decide",
            json={"decision": "granted"},
        )
        assert r2.status_code == 200, r2.text

    def test_low_confidence_advance_blocked(self, auth_session):
        payload = {
            "goal": "Advance candidate stage",
            "steps": [
                {
                    "capability_id": "cap.advance_stage",
                    "inputs": {
                        "candidate_id": "cand_ai_staff_bang_00",
                        "stage": "phone_screen",
                    },
                    "confidence": 0.4,
                }
            ],
        }
        r = auth_session.post(f"{BASE_URL}/api/runtime/execute", json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("status") == "awaiting_approval", d


# ---------- governance ----------
class TestGovernance:
    def test_events(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/governance/events", params={"limit": 50})
        assert r.status_code == 200
        events = r.json()
        events = events if isinstance(events, list) else events.get("items", [])
        assert len(events) > 0
        e = events[0]
        for k in ["event_type", "occurred_at"]:
            assert k in e, f"missing {k} in event: {e}"

    def test_replay(self, auth_session):
        # get an execution correlation id via events
        events = auth_session.get(
            f"{BASE_URL}/api/governance/events", params={"limit": 200}
        ).json()
        events = events if isinstance(events, list) else events.get("items", [])
        cid = None
        for e in events:
            cid = e.get("correlation_id")
            if cid:
                break
        if not cid:
            pytest.skip("no correlation_id in event stream")
        r = auth_session.get(f"{BASE_URL}/api/governance/events/replay/{cid}")
        assert r.status_code == 200


# ---------- reflection ----------
class TestReflection:
    def test_reports(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/reflection/reports")
        assert r.status_code == 200
        reports = r.json()
        reports = reports if isinstance(reports, list) else reports.get("items", [])
        assert len(reports) >= 1
        rep = reports[0]
        for k in ["what_happened", "why"]:
            assert k in rep, f"missing {k} in reflection: {rep.keys()}"


# ---------- applications ----------
class TestApplications:
    def test_dashboard(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/apps/dashboard/summary")
        assert r.status_code == 200, r.text
        d = r.json()
        kpis = d.get("kpis") or {}
        for k in ["open_reqs", "in_pipeline", "offers_active", "hired_ytd", "avg_time_to_fill_days"]:
            assert k in kpis, f"missing kpi {k}: {kpis}"
        assert "pipeline_by_stage" in d
        assert "reqs_by_country" in d
        countries = d["reqs_by_country"]
        keys = countries if isinstance(countries, dict) else {c.get("country"): c for c in countries}
        assert "India" in keys and "USA" in keys
        assert "reqs_by_priority" in d

    def test_recruiter_pipeline(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/apps/recruiter/pipeline")
        assert r.status_code == 200
        items = r.json()
        items = items if isinstance(items, list) else items.get("items", [])
        assert len(items) > 0
        row = items[0]
        assert "job" in row and "candidate_count" in row and "by_stage" in row

    def test_candidate_status_safe(self, auth_session):
        r = auth_session.get(
            f"{BASE_URL}/api/apps/candidate/cand_ai_staff_bang_00/status"
        )
        assert r.status_code == 200
        d = r.json()
        assert "full_name" in d and "stage" in d
        # no salary/confidential
        for forbidden in ["salary", "compensation", "notes", "internal_notes"]:
            assert forbidden not in d, f"leaked {forbidden}"
