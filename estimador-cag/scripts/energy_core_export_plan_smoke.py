from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run(argv: list[str], *, cwd: Path) -> str:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        text=True,
        check=True,
        capture_output=True,
    )
    return completed.stdout


def main() -> int:
    project_root = _project_root()
    repo_root = _repo_root()

    text_output = _run(
        [
            sys.executable,
            "-m",
            "energy_core.export_plan_cli",
            "--project-root",
            ".",
            "--format",
            "text",
            "--fail-on-not-ready",
        ],
        cwd=project_root,
    )
    assert "Energy Aware Code Export Plan" in text_output
    assert "Ready: True" in text_output

    markdown_output = _run(
        [
            sys.executable,
            "-m",
            "energy_core.export_plan_cli",
            "--project-root",
            "estimador-cag",
            "--format",
            "markdown",
            "--fail-on-not-ready",
        ],
        cwd=repo_root,
    )
    assert "# Energy Aware Code Export Plan" in markdown_output
    assert "Ready: True" in markdown_output
    assert "## Excluded items" in markdown_output

    print("Energy Core export plan smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
