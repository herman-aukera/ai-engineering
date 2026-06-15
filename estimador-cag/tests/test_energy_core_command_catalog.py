from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from energy_core.command_catalog import build_command_catalog, format_command_catalog_markdown


def test_command_catalog_lists_supported_surfaces() -> None:
    catalog = build_command_catalog()

    command_ids = {command["id"] for command in catalog["commands"]}

    assert catalog["complete"] is True
    assert "evaluate" in command_ids
    assert "audit_pack" in command_ids
    assert "demo_walkthrough" in command_ids
    assert "ledger_integrity" in command_ids
    assert "nightly_status" in command_ids
    assert "candidate_readiness" in command_ids
    assert "acceptance_trace" in command_ids
    assert "reviewer_snapshot" in command_ids
    assert "package_manifest" in command_ids
    assert "review_pack" in command_ids
    assert "scaffold" in command_ids
    assert "export_plan" in command_ids
    assert "critic_coverage" in command_ids
    assert catalog["mutating_command_ids"] == ["evaluate"]
    assert "audit_pack" in catalog["dry_run_command_ids"]
    assert catalog["repo_root_supported"] is True


def test_command_catalog_markdown_exposes_mutation_behavior() -> None:
    markdown = format_command_catalog_markdown(build_command_catalog())

    assert "# Energy Aware Code Command Catalog" in markdown
    assert "## Mutating commands" in markdown
    assert "- evaluate" in markdown
    assert "### critic_coverage" in markdown
    assert "### candidate_readiness" in markdown
    assert "### acceptance_trace" in markdown
    assert "### demo_walkthrough" in markdown
    assert "### ledger_integrity" in markdown
    assert "### nightly_status" in markdown
    assert "Mutates ledger: True" in markdown
    assert "Mutates ledger: False" in markdown
    assert "does not execute shell actions" in markdown


def test_command_catalog_cli_outputs_json() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.command_catalog_cli",
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
    assert payload["command_total"] >= 22
    assert "evaluate" in payload["mutating_command_ids"]
    command_ids = {command["id"] for command in payload["commands"]}
    assert "demo_walkthrough" in command_ids
    assert "ledger_integrity" in command_ids
    assert "nightly_status" in command_ids
    assert "candidate_readiness" in command_ids
    assert "acceptance_trace" in command_ids


def test_command_catalog_cli_runs_from_repository_root() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    completed = subprocess.run(
        [
            repo_root / "estimador-cag" / ".venv" / "bin" / "python",
            "-m",
            "energy_core.command_catalog_cli",
            "--format",
            "text",
            "--fail-on-incomplete",
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Energy Aware Code Command Catalog" in completed.stdout
    assert "Complete: True" in completed.stdout
