from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from energy_core.specs import summarize_spec_package

ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / ".energy/specs/0001-energy-policy-ledger"


def test_spec_coverage_reports_current_spec_package_complete() -> None:
    summary = summarize_spec_package(SPEC_DIR)

    assert summary["complete"] is True
    assert summary["missing"] == []
    assert summary["present_required"] == summary["total_required"]
    assert summary["required_files"]["energy-policy.yaml"] is True
    assert summary["example_files"]["candidate_accept.json"] is True


def test_spec_coverage_reports_missing_required_artifacts(tmp_path: Path) -> None:
    spec_dir = tmp_path / "spec"
    examples_dir = spec_dir / "examples"
    examples_dir.mkdir(parents=True)
    (spec_dir / "requirements.md").write_text("# Requirements\n", encoding="utf-8")
    (examples_dir / "candidate_accept.json").write_text("{}\n", encoding="utf-8")

    summary = summarize_spec_package(spec_dir)

    assert summary["complete"] is False
    assert "design.md" in summary["missing"]
    assert "examples/candidate_reject_tests_failed.json" in summary["missing"]


def test_spec_coverage_cli_outputs_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.cli",
            "spec-coverage",
            "--spec-dir",
            str(SPEC_DIR),
            "--format",
            "json",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["complete"] is True
    assert payload["missing"] == []


def test_spec_coverage_cli_fails_on_incomplete_spec(tmp_path: Path) -> None:
    spec_dir = tmp_path / "incomplete-spec"
    spec_dir.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.cli",
            "spec-coverage",
            "--spec-dir",
            str(spec_dir),
            "--format",
            "text",
            "--fail-on-incomplete",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Complete: False" in result.stdout
    assert "requirements.md" in result.stdout
