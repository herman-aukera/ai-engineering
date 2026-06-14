from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / ".energy/specs/0001-energy-policy-ledger/energy-policy.yaml"


def run_command(command: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


def main() -> int:
    text = run_command(
        [
            sys.executable,
            "-m",
            "energy_core.constraints_cli",
            "--policy",
            str(POLICY),
            "--format",
            "text",
            "--fail-on-incomplete",
        ]
    )
    if "Complete: True" not in text.stdout:
        raise AssertionError(text.stdout)

    markdown = run_command(
        [
            sys.executable,
            "-m",
            "energy_core.constraints_cli",
            "--policy",
            str(POLICY),
            "--format",
            "markdown",
            "--fail-on-incomplete",
        ]
    )
    if "# Energy Aware Code Constraint Index" not in markdown.stdout:
        raise AssertionError(markdown.stdout)

    json_output = run_command(
        [
            sys.executable,
            "-m",
            "energy_core.constraints_cli",
            "--policy",
            str(POLICY),
            "--format",
            "json",
        ]
    )
    payload = json.loads(json_output.stdout)
    if payload["complete"] is not True:
        raise AssertionError(payload)

    print("Energy Core constraint smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
