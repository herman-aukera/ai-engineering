from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from energy_core.acceptance_trace import (
    build_acceptance_trace,
    format_acceptance_trace_markdown,
)


def test_acceptance_trace_is_complete_for_baseline_spec() -> None:
    trace = build_acceptance_trace(Path("."))

    assert trace["complete"] is True
    assert trace["criterion_total"] == 9
    assert trace["traced_total"] == 9
    assert trace["missing_trace"] == []
    assert trace["missing_required_acceptance"] == []


def test_acceptance_trace_links_ledger_acceptance_to_ledger_surface() -> None:
    trace = build_acceptance_trace(Path("."))
    row_by_id = {row["criterion_id"]: row for row in trace["rows"]}

    assert "ledger_integrity" in row_by_id["A9"]["surfaces"]
    assert "git_diff" in row_by_id["A9"]["evidence"]


def test_acceptance_trace_markdown_is_reviewer_readable() -> None:
    markdown = format_acceptance_trace_markdown(build_acceptance_trace(Path(".")))

    assert "# Energy Aware Code Acceptance Trace" in markdown
    assert "- Complete: True" in markdown
    assert "Policy loading returns a typed policy" in markdown
    assert "Decision ledger appends JSONL rows" in markdown


def test_acceptance_trace_cli_outputs_json_from_project_root() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.acceptance_trace_cli",
            "--format",
            "json",
            "--fail-on-incomplete",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(completed.stdout)

    assert payload["complete"] is True
    assert payload["criterion_total"] == 9
