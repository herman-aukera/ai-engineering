from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from energy_core.export_plan import build_export_plan, format_export_plan_markdown


def test_export_plan_is_ready_for_current_incubator() -> None:
    plan = build_export_plan(Path("."))

    assert plan["ready"] is True
    assert plan["package_manifest_complete"] is True
    assert plan["copy_item_present"] == plan["copy_item_total"]
    assert plan["missing_copy_items"] == []
    assert any(item["group"] == "package" for item in plan["copy_items"])
    assert any(item["group"] == "incubator_root" for item in plan["excluded_items"])


def test_export_plan_markdown_lists_steps_and_non_goals() -> None:
    markdown = format_export_plan_markdown(build_export_plan(Path(".")))

    assert "# Energy Aware Code Export Plan" in markdown
    assert "Ready: True" in markdown
    assert "Generate standalone scaffold" in markdown
    assert "does not copy files automatically" in markdown


def test_export_plan_cli_runs_from_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.export_plan_cli",
            "--project-root",
            "estimador-cag",
            "--format",
            "text",
            "--fail-on-not-ready",
        ],
        cwd=repo_root,
        text=True,
        check=True,
        capture_output=True,
    )

    assert "Energy Aware Code Export Plan" in result.stdout
    assert "Ready: True" in result.stdout
