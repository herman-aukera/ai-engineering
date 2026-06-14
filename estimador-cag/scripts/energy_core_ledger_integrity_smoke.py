from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    repo_root = project_root.parent

    project_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.ledger_integrity_cli",
            "--format",
            "markdown",
            "--fail-on-invalid",
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=True,
    )
    if "# Energy Aware Code Ledger Integrity" not in project_result.stdout:
        raise AssertionError("Ledger integrity Markdown heading is missing.")
    if "Complete: True" not in project_result.stdout:
        raise AssertionError("Committed decision ledger is not integrity-clean.")

    root_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.ledger_integrity_cli",
            "--ledger",
            ".energy/specs/0001-energy-policy-ledger/decisions.jsonl",
            "--format",
            "text",
            "--fail-on-invalid",
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
    )
    if "Energy Aware Code Ledger Integrity" not in root_result.stdout:
        raise AssertionError("Ledger integrity did not run from repository root.")

    print("Energy Core ledger integrity smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
