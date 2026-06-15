from pathlib import Path
import subprocess
import sys

from energy_core.policy_roadmap import (
    build_policy_roadmap,
    format_policy_roadmap_markdown,
    format_policy_roadmap_text,
)

POLICY = Path(".energy/specs/0001-energy-policy-ledger/energy-policy.yaml")


def test_policy_roadmap_is_complete_and_honest_about_policy_only_constraints() -> None:
    roadmap = build_policy_roadmap(POLICY)

    assert roadmap["complete"] is True
    assert roadmap["coverage_level"] == "partial"
    assert roadmap["policy_only_total"] == 4
    assert roadmap["missing_roadmap"] == []
    assert {entry["constraint_id"] for entry in roadmap["entries"]} == {
        "executor_self_approved",
        "leaked_proprietary_code",
        "unsafe_command",
        "wrong_branch",
    }


def test_policy_roadmap_formats_text_and_markdown() -> None:
    roadmap = build_policy_roadmap(POLICY)

    text = format_policy_roadmap_text(roadmap)
    markdown = format_policy_roadmap_markdown(roadmap)

    assert "Energy Aware Code Policy Roadmap" in text
    assert "Complete: True" in text
    assert "# Energy Aware Code Policy Roadmap" in markdown
    assert "## Policy-only roadmap" in markdown
    assert "## Execution boundaries" in markdown


def test_policy_roadmap_cli_works_from_repo_root() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.policy_roadmap_cli",
            "--policy",
            ".energy/specs/0001-energy-policy-ledger/energy-policy.yaml",
            "--format",
            "markdown",
            "--fail-on-incomplete",
        ],
        cwd=Path("..").resolve(),
        text=True,
        capture_output=True,
        check=True,
    )

    assert "# Energy Aware Code Policy Roadmap" in result.stdout
    assert "- Complete: True" in result.stdout
