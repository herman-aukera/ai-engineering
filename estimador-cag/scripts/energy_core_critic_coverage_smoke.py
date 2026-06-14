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
            "energy_core.critic_coverage_cli",
            "--format",
            "markdown",
            "--fail-on-unclassified",
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=True,
    )
    if "# Energy Aware Code Critic Coverage" not in project_result.stdout:
        raise AssertionError("Critic coverage Markdown heading is missing.")
    if "Complete: True" not in project_result.stdout:
        raise AssertionError("Critic coverage did not report complete classification.")
    if "unsafe_command" not in project_result.stdout:
        raise AssertionError("Critic coverage did not expose policy-only constraints.")

    root_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.critic_coverage_cli",
            "--policy",
            ".energy/specs/0001-energy-policy-ledger/energy-policy.yaml",
            "--format",
            "text",
            "--fail-on-unclassified",
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
    )
    if "Coverage level: partial" not in root_result.stdout:
        raise AssertionError("Critic coverage did not report partial coverage honestly.")

    print("Energy Core critic coverage smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
