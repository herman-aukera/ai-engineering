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

    assert report["complete"] is True
    assert report["missing_surface_ids"] == []
    assert report["complete_surface_total"] == report["surface_total"]
    surface_ids = {row["surface_id"] for row in report["rows"]}
    assert "acceptance_trace" in surface_ids
    assert "candidate_readiness" in surface_ids
    assert "command_catalog" in surface_ids
    assert "critic_coverage" in surface_ids
    assert "ledger_integrity" in surface_ids
    assert "review_gap_register" in surface_ids


def test_surface_consistency_handles_intrinsic_surfaces() -> None:
    report = build_surface_consistency(Path("."))
    rows = {row["surface_id"]: row for row in report["rows"]}

    assert rows["command_catalog"]["catalog"] is True
    assert rows["command_catalog"]["reviewer"] is True
    assert rows["reviewer_snapshot"]["catalog"] is True
    assert rows["reviewer_snapshot"]["reviewer"] is True


def test_surface_consistency_marks_review_gap_register_complete() -> None:
    report = build_surface_consistency(Path("."))
    rows = {row["surface_id"]: row for row in report["rows"]}

    assert rows["review_gap_register"]["complete"] is True
    assert rows["review_gap_register"]["catalog"] is True
    assert rows["review_gap_register"]["reviewer"] is True
    assert rows["review_gap_register"]["review_pack"] is True
    assert rows["review_gap_register"]["package"] is True


def test_surface_consistency_marks_acceptance_trace_complete() -> None:
    report = build_surface_consistency(Path("."))
    rows = {row["surface_id"]: row for row in report["rows"]}

    assert rows["acceptance_trace"]["complete"] is True
    assert rows["acceptance_trace"]["catalog"] is True
    assert rows["acceptance_trace"]["reviewer"] is True
    assert rows["acceptance_trace"]["review_pack"] is True
    assert rows["acceptance_trace"]["package"] is True


def test_surface_consistency_markdown_is_reviewer_readable() -> None:
    markdown = format_surface_consistency_markdown(build_surface_consistency(Path(".")))

    assert "# Energy Aware Code Surface Consistency" in markdown
    assert "- Complete: True" in markdown
    assert "### acceptance_trace" in markdown
    assert "### candidate_readiness" in markdown
    assert "### review_gap_register" in markdown
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

    assert payload["complete"] is True
    assert payload["missing_surface_ids"] == []
