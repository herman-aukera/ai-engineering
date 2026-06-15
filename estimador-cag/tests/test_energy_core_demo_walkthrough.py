from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from energy_core.demo_walkthrough import (
    build_demo_walkthrough,
    format_demo_walkthrough_markdown,
)


def test_demo_walkthrough_is_complete() -> None:
    report = build_demo_walkthrough(Path("."))

    assert report["complete"] is True
    assert report["step_total"] == 5
    assert report["missing_step_surfaces"] == []
    assert report["blocking_gap_total"] == 0


def test_demo_walkthrough_markdown_lists_demo_sequence() -> None:
    markdown = format_demo_walkthrough_markdown(build_demo_walkthrough(Path(".")))

    assert "# Energy Aware Code Demo Walkthrough" in markdown
    assert "Step 1: Open the generated review pack" in markdown
    assert "Step 5: Run the one-command full gate" in markdown
    assert "Demo walkthrough does not call LLM providers" in markdown


def test_demo_walkthrough_cli_outputs_json() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.demo_walkthrough_cli",
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
    assert payload["step_total"] == 5
