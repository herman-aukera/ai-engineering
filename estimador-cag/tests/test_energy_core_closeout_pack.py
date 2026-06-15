from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from energy_core.closeout_pack import build_closeout_pack, format_closeout_pack_markdown


def test_closeout_pack_is_complete() -> None:
    report = build_closeout_pack(Path("."))

    assert report["complete"] is True
    assert report["section_total"] == 5
    assert report["complete_section_total"] == 5
    assert report["incomplete_sections"] == []
    assert report["blocking_gap_total"] == 0
    assert report["blocking_conflict_total"] == 0
    assert report["review_pack_file_total"] >= 14
    assert report["surface_total"] >= 13


def test_closeout_pack_markdown_lists_sections() -> None:
    markdown = format_closeout_pack_markdown(build_closeout_pack(Path(".")))

    assert "# Energy Aware Code Closeout Pack" in markdown
    assert "Incubator status" in markdown
    assert "Reviewer evidence index" in markdown
    assert "Acceptance evidence trace" in markdown
    assert "Day-end handoff checklist" in markdown
    assert "Next-slice roadmap" in markdown
    assert "Closeout pack does not call LLM providers" in markdown


def test_closeout_pack_cli_outputs_json() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.closeout_pack_cli",
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
    assert payload["section_total"] == 5
