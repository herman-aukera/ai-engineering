from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from energy_core.surface_consistency import (
    build_surface_consistency,
    format_surface_consistency_markdown,
)


def test_surface_consistency_reports_reviewer_surfaces() -> None:
    report = build_surface_consistency(Path("."))

    assert report["surface_total"] >= 1
    assert report["complete_surface_total"] <= report["surface_total"]
    surface_ids = {row["surface_id"] for row in report["rows"]}
    assert "candidate_readiness" in surface_ids
    assert "critic_coverage" in surface_ids
    assert "ledger_integrity" in surface_ids


def test_surface_consistency_markdown_is_reviewer_readable() -> None:
    markdown = format_surface_consistency_markdown(build_surface_consistency(Path(".")))

    assert "# Energy Aware Code Surface Consistency" in markdown
    assert "### candidate_readiness" in markdown
    assert "Review pack:" in markdown
    assert "Package manifest:" in markdown


def test_surface_consistency_cli_outputs_json() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.surface_consistency_cli",
            "--format",
            "json",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(completed.stdout)

    assert payload["surface_total"] >= 1
    assert isinstance(payload["missing_surface_ids"], list)
