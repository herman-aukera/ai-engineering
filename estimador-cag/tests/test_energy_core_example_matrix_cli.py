import subprocess
import sys
from pathlib import Path

SPEC_DIR = Path(".energy/specs/0001-energy-policy-ledger")
POLICY = SPEC_DIR / "energy-policy.yaml"
EVIDENCE = SPEC_DIR / "evidence.jsonl"


def test_example_matrix_cli_from_project_root() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.examples_cli",
            "--spec-dir",
            str(SPEC_DIR),
            "--policy",
            str(POLICY),
            "--evidence",
            str(EVIDENCE),
            "--format",
            "markdown",
            "--fail-on-mismatch",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "# Energy Aware Code Example Matrix" in result.stdout
    assert "Passed cases: 4/4" in result.stdout


def test_example_matrix_cli_from_repository_root() -> None:
    repo_root = Path.cwd().parent
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.examples_cli",
            "--spec-dir",
            str(SPEC_DIR),
            "--policy",
            str(POLICY),
            "--evidence",
            str(EVIDENCE),
            "--format",
            "text",
            "--fail-on-mismatch",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Energy Aware Code Example Matrix" in result.stdout
    assert "Passed cases: 4/4" in result.stdout
