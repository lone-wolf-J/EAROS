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
