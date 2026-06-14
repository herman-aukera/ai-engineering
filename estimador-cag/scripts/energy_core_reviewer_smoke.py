from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run(command: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr, file=sys.stderr)
        raise SystemExit(completed.returncode)
    return completed.stdout


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    repo_root = project_root.parent

    project_output = _run(
        [
            sys.executable,
            "-m",
            "energy_core.reviewer_cli",
            "--project-root",
            ".",
            "--format",
            "markdown",
            "--fail-on-incomplete",
        ],
        project_root,
    )
    if "# Energy Aware Code Reviewer Snapshot" not in project_output:
        print(project_output)
        print("Reviewer smoke did not print snapshot title", file=sys.stderr)
        return 1
    if "Complete: True" not in project_output:
        print(project_output)
        print("Reviewer smoke did not report Complete: True", file=sys.stderr)
        return 1

    root_output = _run(
        [
            sys.executable,
            "-m",
            "energy_core.reviewer_cli",
            "--project-root",
            "estimador-cag",
            "--format",
            "text",
            "--fail-on-incomplete",
        ],
        repo_root,
    )
    if "Complete: True" not in root_output:
        print(root_output)
        print("Repo-root reviewer smoke did not report Complete: True", file=sys.stderr)
        return 1

    print("Energy Core reviewer smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
