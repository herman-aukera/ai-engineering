from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from energy_core.review_gap_register import (
    build_review_gap_register,
    format_review_gap_register_markdown,
)


def test_review_gap_register_is_complete_without_blocking_gaps() -> None:
    register = build_review_gap_register(Path("."))

    assert register["complete"] is True
    assert register["blocking_gap_total"] == 0
    assert register["gap_total"] >= 1
    ids = {gap["id"] for gap in register["gaps"]}
    assert "policy_only:unsafe_command" in ids
    assert "candidate_not_ready:candidate_repair_missing_evidence.json" in ids


def test_review_gap_register_markdown_is_reviewer_readable() -> None:
    markdown = format_review_gap_register_markdown(build_review_gap_register(Path(".")))

    assert "# Energy Aware Code Review Gap Register" in markdown
    assert "- Complete: True" in markdown
    assert "## Gaps" in markdown
    assert "policy_only:wrong_branch" in markdown


def test_review_gap_register_cli_outputs_json() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.review_gap_register_cli",
            "--format",
            "json",
            "--fail-on-blocking",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(completed.stdout)

    assert payload["complete"] is True
    assert payload["blocking_gap_total"] == 0
