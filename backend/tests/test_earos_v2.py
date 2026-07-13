"""
EAROS iteration-2 backend API tests.
Covers: mission snapshot, agents(17), integrations(24), scenarios(8+run),
intake (LLM w/ generous timeout, fallback OK), sourcing sweep (10 channels),
resume analyze, outreach pack (3 email variants), screening rubric (8 dims),
voice interview (plan/turn/summarize), what-if simulation (13 pts).
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


@pytest.fixture(scope="module")
def auth_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/dev-login", params={"email": RECRUITER_EMAIL})
    assert r.status_code == 200, r.text
    return s


# ---------- Mission Control ----------
class TestMission:
    def test_snapshot(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/mission/snapshot", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "counts" in d
        counts = d["counts"]
        assert counts.get("events_total", 0) >= 1
        # agent pulse = 17
        pulse = d.get("agent_pulse") or []
        assert len(pulse) == 17, f"agent_pulse len {len(pulse)}"
        # ambient activity
        ambient = d.get("ambient_activity") or []
        assert len(ambient) >= 1
        # recent events
        assert d.get("recent_events") is not None


# ---------- Agents + Integrations ----------
class TestAgentsAndIntegrations:
    def test_agents_17(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/platform/agents")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 17, f"expected 17 agents got {len(data)}"
        # spot-check fields
        first = data[0]
        for key in ["agent_id", "name", "category"]:
            assert key in first, f"missing {key}: {first.keys()}"

    def test_integrations_24(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/platform/integrations")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 24, f"expected 24 integrations got {len(data)}"
        first = data[0]
        for key in ["integration_id", "name", "category", "connection_status"]:
            assert key in first, f"missing {key}: {first.keys()}"


# ---------- Scenarios ----------
class TestScenarios:
    def test_list_8(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/scenarios")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 8, f"expected 8 scenarios got {len(data)}"
        ids = [s.get("scenario_id") or s.get("id") for s in data]
        assert "scn.java_chennai" in ids
        assert "scn.sfdc_arch" in ids

    def test_run_java_chennai(self, auth_session):
        r = auth_session.post(
            f"{BASE_URL}/api/scenarios/scn.java_chennai/run-sync", timeout=60
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert "correlation_id" in d
        assert "candidates_screened" in d
        assert isinstance(d["candidates_screened"], list)


# ---------- Intake (LLM, fallback OK) ----------
class TestIntake:
    def test_analyze_java_brief(self, auth_session):
        brief = (
            "We need a Senior Java Engineer in Chennai, India. 6-10 years experience, "
            "must have Java, Spring Boot, microservices, and Kafka. Salary ~28LPA. "
            "Full-time, hybrid, urgent close."
        )
        r = auth_session.post(
            f"{BASE_URL}/api/intake/analyze", json={"brief": brief}, timeout=90
        )
        assert r.status_code == 200, r.text
        d = r.json()
        intake = d.get("intake") or {}
        must = intake.get("must_have_skills") or []
        assert any("java" in str(s).lower() for s in must), f"no Java in must: {must}"
        assert intake.get("generated_jd"), "no generated_jd"


# ---------- Sourcing ----------
class TestSourcing:
    def test_sweep_10_channels(self, auth_session):
        r = auth_session.get(
            f"{BASE_URL}/api/sourcing/sweep/job_ai_staff_bang", timeout=15
        )
        assert r.status_code == 200, r.text
        d = r.json()
        channels = d.get("channels") or d.get("results") or (d if isinstance(d, list) else [])
        assert len(channels) == 10, f"expected 10 channels, got {len(channels)}"
        first = channels[0]
        assert "matches" in first
        assert "unique_matches" in first or "unique" in first
        assert "quality_score" in first or "quality" in first


# ---------- Resume ----------
class TestResume:
    def test_analyze(self, auth_session):
        payload = {
            "resume_text": (
                "John Doe\nSenior Software Engineer\n8 years experience\n"
                "Skills: Python, FastAPI, Kafka, AWS, Docker, Kubernetes\n"
                "Experience: Built distributed systems at scale."
            ),
            "job_id": "job_ai_staff_bang",
        }
        r = auth_session.post(f"{BASE_URL}/api/resume/analyze", json=payload, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "parsed" in d and "fit" in d and "client_summary" in d
        fit = d["fit"] or {}
        assert "fit_score" in fit or "coverage" in fit


# ---------- Outreach ----------
class TestOutreach:
    def test_pack_3_variants(self, auth_session):
        r = auth_session.get(
            f"{BASE_URL}/api/outreach/pack/cand_ai_staff_bang_00", timeout=30
        )
        assert r.status_code == 200, r.text
        d = r.json()
        # variants may be nested under 'channels'
        ch = d.get("channels") or {}
        variants = d.get("email_variants") or ch.get("email_variants") or []
        assert len(variants) == 3, f"expected 3 email variants got {len(variants)}"


# ---------- Screening ----------
class TestScreening:
    def test_rubric_8_dims(self, auth_session):
        r = auth_session.post(
            f"{BASE_URL}/api/screening/rubric",
            json={"candidate_id": "cand_ai_staff_bang_00"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        dims = d.get("rubric") or d.get("dimensions") or d.get("scores") or []
        if isinstance(dims, dict):
            dims = list(dims.values())
        assert len(dims) == 8, f"expected 8 dimensions got {len(dims)}"
        assert "composite" in d or "composite_score" in d


# ---------- Voice ----------
class TestVoice:
    def test_plan_and_turn(self, auth_session):
        r = auth_session.get(
            f"{BASE_URL}/api/voice/plan/cand_ai_staff_bang_00", timeout=15
        )
        assert r.status_code == 200, r.text
        r2 = auth_session.get(
            f"{BASE_URL}/api/voice/turn/cand_ai_staff_bang_00/0", timeout=15
        )
        assert r2.status_code == 200, r2.text
        d = r2.json()
        assert "question" in d or "transcript" in d or "answer" in d


# ---------- What-if ----------
class TestWhatIf:
    def test_simulate_trajectory(self, auth_session):
        payload = {
            "attrition_pct": 0.15,
            "hiring_freeze": False,
            "budget_delta_pct": 0.1,
            "bangalore_expansion": True,
            "ai_engineering_doubles": True,
            "horizon_months": 12,
        }
        r = auth_session.post(
            f"{BASE_URL}/api/simulate/what-if", json=payload, timeout=15
        )
        assert r.status_code == 200, r.text
        d = r.json()
        traj = d.get("trajectory") or []
        assert len(traj) == 13, f"expected 13 trajectory points got {len(traj)}"
        assert d.get("recommendation") or d.get("reasoning")
