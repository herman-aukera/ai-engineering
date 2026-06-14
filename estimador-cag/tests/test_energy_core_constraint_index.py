from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from energy_core.constraints import build_constraint_index
from energy_core.policy import load_policy

POLICY_PATH = Path(".energy/specs/0001-energy-policy-ledger/energy-policy.yaml")


def test_constraint_index_summarizes_policy_contract() -> None:
    policy = load_policy(POLICY_PATH)

    index = build_constraint_index(policy)

    assert index["complete"] is True
    assert index["policy_id"] == "energy-code-default"
    assert index["counts"]["hard_reject"] >= 1
    assert index["counts"]["hard_repair"] >= 1
    assert index["counts"]["soft"] >= 1
    assert index["missing_evidence_types"] == []
    assert "pytest_output" in index["required_acceptance_evidence"]


def test_constraint_index_cli_outputs_markdown() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.constraints_cli",
            "--policy",
            str(POLICY_PATH),
            "--format",
            "markdown",
            "--fail-on-incomplete",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "# Energy Aware Code Constraint Index" in result.stdout
    assert "Complete: True" in result.stdout
    assert "pytest_output" in result.stdout


def test_constraint_index_cli_outputs_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.constraints_cli",
            "--policy",
            str(POLICY_PATH),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["complete"] is True
    assert payload["counts"]["evidence_types"] >= 1


def test_constraint_index_cli_works_from_repository_root() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    python_bin = repo_root / ".venv" / "bin" / "python"
    if not python_bin.exists():
        python_bin = Path(sys.executable)

    result = subprocess.run(
        [
            str(python_bin),
            "-m",
            "energy_core.constraints_cli",
            "--policy",
            ".energy/specs/0001-energy-policy-ledger/energy-policy.yaml",
            "--format",
            "text",
            "--fail-on-incomplete",
        ],
        cwd=repo_root.parent,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Energy Aware Code Constraint Index" in result.stdout
    assert "Complete: True" in result.stdout
