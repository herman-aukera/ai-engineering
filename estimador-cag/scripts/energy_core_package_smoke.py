from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    commands = [
        [
            sys.executable,
            "-m",
            "energy_core.package_cli",
            "--project-root",
            ".",
            "--format",
            "text",
            "--fail-on-incomplete",
        ],
        [
            sys.executable,
            "-m",
            "energy_core.package_cli",
            "--project-root",
            ".",
            "--format",
            "markdown",
            "--fail-on-incomplete",
        ],
    ]

    for command in commands:
        completed = subprocess.run(
            command,
            cwd=project_root,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            print(completed.stdout)
            print(completed.stderr, file=sys.stderr)
            return completed.returncode
        if "Complete: True" not in completed.stdout:
            print(completed.stdout)
            print("Package manifest smoke did not report Complete: True", file=sys.stderr)
            return 1

    repo_root = project_root.parent
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.package_cli",
            "--project-root",
            "estimador-cag",
            "--format",
            "text",
            "--fail-on-incomplete",
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr, file=sys.stderr)
        return completed.returncode
    if "Complete: True" not in completed.stdout:
        print(completed.stdout)
        print("Repo-root package manifest smoke did not report Complete: True", file=sys.stderr)
        return 1

    print("Energy Core package smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
