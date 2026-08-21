"""Contracts for operator-facing infrastructure validation artifacts.

These tests execute only local Node and shell syntax checks. They never contact an
external database, identity provider, Docker daemon, or production environment.
"""

from pathlib import Path
import subprocess


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def run_node(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", *arguments],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_infrastructure_preflight_accepts_controlled_nonsecret_fixture() -> None:
    result = run_node(
        "scripts/validate-infrastructure.mjs",
        "--env-file",
        "ops/staging-validation.valid.testvars",
    )

    assert result.returncode == 0, result.stderr
    assert "infrastructure preflight passed" in result.stdout


def test_infrastructure_preflight_rejects_placeholder_staging_inputs() -> None:
    result = run_node(
        "scripts/validate-infrastructure.mjs",
        "--env-file",
        "ops/staging-validation.testvars",
    )

    assert result.returncode != 0
    assert "must be supplied" in result.stderr


def test_backup_restore_evidence_validator_accepts_complete_isolated_recovery_record() -> None:
    result = run_node(
        "scripts/verify-backup-evidence.mjs",
        "ops/backup-restore-evidence.valid.test.json",
    )

    assert result.returncode == 0, result.stderr
    assert "backup/restore evidence passed" in result.stdout


def test_backup_restore_evidence_validator_rejects_example_placeholders() -> None:
    result = run_node(
        "scripts/verify-backup-evidence.mjs",
        "ops/backup-restore-evidence.example.json",
    )

    assert result.returncode != 0
    assert "must contain recorded evidence" in result.stderr


def test_compose_harness_is_syntax_valid_and_cleans_up_its_stack() -> None:
    result = subprocess.run(
        ["bash", "-n", "scripts/run-compose-validation.sh"],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    harness = (REPOSITORY_ROOT / "scripts/run-compose-validation.sh").read_text(encoding="utf8")
    assert "docker compose" in harness
    assert "trap cleanup EXIT" in harness
    assert "validate-infrastructure.mjs --runtime" in harness


def test_ci_workflow_keeps_runtime_execution_manual_and_secret_backed() -> None:
    workflow = (REPOSITORY_ROOT / ".github/workflows/infrastructure-validation.yml").read_text(encoding="utf8")

    assert "workflow_dispatch:" in workflow
    assert "run_runtime:" in workflow
    assert "environment: earos-staging" in workflow
    assert "secrets.EAROS_STAGING_BACKEND_ENV" in workflow
    assert "secrets.EAROS_STAGING_VALIDATION_ENV" in workflow
    assert "bash scripts/run-compose-validation.sh" in workflow
    assert "rm -f backend/.env ops/staging-validation.env" in workflow


def test_self_contained_compose_smoke_is_built_and_exercised_in_ci() -> None:
    compose = (REPOSITORY_ROOT / "docker-compose.infrastructure-smoke.yml").read_text(encoding="utf8")
    harness = (REPOSITORY_ROOT / "scripts" / "run-infrastructure-smoke.sh").read_text(encoding="utf8")
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "infrastructure-validation.yml").read_text(encoding="utf8")

    assert "mongo:7.0" in compose
    assert "EAROS_ENV: production" in compose
    assert "EAROS_ENABLE_DEV_LOGIN: \"false\"" in compose
    assert "condition: service_healthy" in compose
    assert "docker compose" in harness
    assert "/api/ready" in harness
    assert "EAROS frontend container" in harness
    assert "for route in /ats /ats/workflows /interview" in harness
    assert "down --volumes --remove-orphans" in harness
    assert "scripts/run-infrastructure-smoke.sh" in workflow
    assert '"docker-compose.infrastructure-smoke.yml"' in workflow
    assert '"backend/requirements.txt"' in workflow


def test_isolated_authenticated_smoke_never_enables_dev_login_in_production_stack() -> None:
    production_smoke = (REPOSITORY_ROOT / "docker-compose.infrastructure-smoke.yml").read_text(encoding="utf8")
    authenticated_smoke = (REPOSITORY_ROOT / "docker-compose.infrastructure-auth-smoke.yml").read_text(encoding="utf8")
    harness = (REPOSITORY_ROOT / "scripts" / "run-infrastructure-auth-smoke.sh").read_text(encoding="utf8")
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "infrastructure-validation.yml").read_text(encoding="utf8")

    assert "EAROS_ENV: production" in production_smoke
    assert 'EAROS_ENABLE_DEV_LOGIN: "false"' in production_smoke
    assert "EAROS_ENV: development" in authenticated_smoke
    assert 'EAROS_ENABLE_DEV_LOGIN: "true"' in authenticated_smoke
    assert "/api/auth/dev-login" in harness
    assert "/api/ats/requisitions" in harness
    assert "/api/ats/interviews" in harness
    assert "run-infrastructure-auth-smoke.sh" in workflow


def test_required_container_dependencies_exclude_optional_private_llm_client() -> None:
    requirements = (REPOSITORY_ROOT / "backend" / "requirements.txt").read_text(encoding="utf8")
    planner = (REPOSITORY_ROOT / "backend" / "platform_core" / "planner.py").read_text(encoding="utf8")
    intake = (REPOSITORY_ROOT / "backend" / "intelligence" / "intake.py").read_text(encoding="utf8")

    assert "emergentintegrations" not in requirements
    assert "try:" in planner and "except Exception:" in planner
    assert "try:" in intake and "except Exception:" in intake


def test_required_container_dependencies_include_production_auth_http_client() -> None:
    requirements = (REPOSITORY_ROOT / "backend" / "requirements.txt").read_text(encoding="utf8")
    auth = (REPOSITORY_ROOT / "backend" / "applications" / "auth.py").read_text(encoding="utf8")

    assert "import httpx" in auth
    assert "httpx>=" in requirements


def test_frontend_container_installs_build_tooling_before_production_runtime() -> None:
    dockerfile = (REPOSITORY_ROOT / "frontend" / "Dockerfile").read_text(encoding="utf8")

    assert "yarn install --frozen-lockfile --ignore-engines --production=false" in dockerfile
    assert "FROM nginx:1.27-alpine\nENV NODE_ENV=production" in dockerfile
