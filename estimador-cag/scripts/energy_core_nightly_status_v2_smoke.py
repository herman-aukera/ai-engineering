from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from energy_core.nightly_status import build_nightly_status, format_nightly_status_markdown


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    repo_root = project_root.parent

    status = build_nightly_status(project_root)
    assert status["complete"] is True
    assert status["section_total"] == 5
    assert status["section_complete_total"] == 5

    markdown = format_nightly_status_markdown(status)
    assert "# Energy Aware Code Nightly Status" in markdown
    assert "M1 Policy health" in markdown
    assert "M5 Maintainer handoff" in markdown

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.nightly_status_cli",
            "--project-root",
            "estimador-cag",
            "--format",
            "text",
            "--fail-on-incomplete",
        ],
        cwd=repo_root,
        text=True,
        check=True,
        capture_output=True,
    )
    assert "Energy Aware Code Nightly Status" in result.stdout
    assert "Complete: True" in result.stdout

    print("Energy Core nightly status smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
