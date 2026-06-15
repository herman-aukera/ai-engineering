from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run(argv: list[str], *, cwd: Path) -> str:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        text=True,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr, file=sys.stderr)
        raise SystemExit(completed.returncode)
    return completed.stdout


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    repo_root = project_root.parent

    text_output = _run(
        [
            sys.executable,
            "-m",
            "energy_core.extraction_readiness_cli",
            "--project-root",
            ".",
            "--format",
            "text",
        ],
        cwd=project_root,
    )
    if "Energy Aware Code Extraction Readiness" not in text_output:
        print(text_output)
        raise SystemExit("Extraction readiness text output is missing the title.")

    markdown_output = _run(
        [
            sys.executable,
            "-m",
            "energy_core.extraction_readiness_cli",
            "--project-root",
            "estimador-cag",
            "--format",
            "markdown",
        ],
        cwd=repo_root,
    )
    if "# Energy Aware Code Extraction Readiness" not in markdown_output:
        print(markdown_output)
        raise SystemExit("Extraction readiness markdown output is missing the title.")

    print("Energy Core extraction readiness smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
