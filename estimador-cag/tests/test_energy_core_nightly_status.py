from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from energy_core.nightly_status import build_nightly_status, format_nightly_status_markdown


def test_nightly_status_has_five_complete_sections() -> None:
    status = build_nightly_status(Path("."))

    assert status["complete"] is True
    assert status["section_total"] == 5
    assert status["section_complete_total"] == 5
    assert [section["id"] for section in status["sections"]] == [
        "policy_health",
        "evidence_completeness",
        "command_safety_surface",
        "release_export_readiness",
        "maintainer_handoff",
    ]


def test_nightly_status_markdown_lists_all_milestones() -> None:
    markdown = format_nightly_status_markdown(build_nightly_status(Path(".")))

    assert "# Energy Aware Code Nightly Status" in markdown
    assert "M1 Policy health" in markdown
    assert "M2 Evidence completeness" in markdown
    assert "M3 Command safety surface" in markdown
    assert "M4 Release/export readiness" in markdown
    assert "M5 Maintainer handoff" in markdown


def test_nightly_status_cli_runs_from_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[2]
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
