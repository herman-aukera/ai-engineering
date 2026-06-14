import subprocess
import sys
from pathlib import Path

from energy_core.critic_coverage import (
    build_critic_coverage,
    format_critic_coverage_markdown,
    format_critic_coverage_text,
)

POLICY = Path(".energy/specs/0001-energy-policy-ledger/energy-policy.yaml")


def test_critic_coverage_classifies_all_constraints() -> None:
    coverage = build_critic_coverage(POLICY)

    assert coverage["complete"] is True
    assert coverage["coverage_level"] == "partial"
    assert coverage["unclassified_constraint_ids"] == []
    assert "tests_failed" in coverage["enforced_constraint_ids"]
    assert "missing_required_evidence" in coverage["enforced_constraint_ids"]
    assert "unsafe_command" in coverage["policy_only_constraint_ids"]
    assert "wrong_branch" in coverage["policy_only_constraint_ids"]
    assert coverage["enforced_total"] + coverage["policy_only_total"] == coverage["constraint_total"]


def test_critic_coverage_formats_text_and_markdown() -> None:
    coverage = build_critic_coverage(POLICY)

    text = format_critic_coverage_text(coverage)
    markdown = format_critic_coverage_markdown(coverage)

    assert "Energy Aware Code Critic Coverage" in text
    assert "Coverage level: partial" in text
    assert "# Energy Aware Code Critic Coverage" in markdown
    assert "## Policy-only constraints" in markdown
    assert "unsafe_command" in markdown


def test_critic_coverage_cli_from_project_root() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.critic_coverage_cli",
            "--format",
            "markdown",
            "--fail-on-unclassified",
        ],
        text=True,
        capture_output=True,
        check=True,
    )

    assert "# Energy Aware Code Critic Coverage" in result.stdout
    assert "Complete: True" in result.stdout


def test_critic_coverage_cli_from_repository_root() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.critic_coverage_cli",
            "--policy",
            ".energy/specs/0001-energy-policy-ledger/energy-policy.yaml",
            "--format",
            "text",
            "--fail-on-unclassified",
        ],
        cwd=Path(".."),
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Energy Aware Code Critic Coverage" in result.stdout
    assert "Complete: True" in result.stdout
