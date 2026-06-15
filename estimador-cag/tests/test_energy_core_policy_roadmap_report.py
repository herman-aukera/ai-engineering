from pathlib import Path

from energy_core.policy_roadmap import (
    build_policy_roadmap,
    format_policy_roadmap_markdown,
    format_policy_roadmap_text,
)

POLICY = Path(".energy/specs/0001-energy-policy-ledger/energy-policy.yaml")


def test_policy_roadmap_is_complete_and_explicit() -> None:
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
