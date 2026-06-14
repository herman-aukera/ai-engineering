from pathlib import Path

from energy_core.reviewer_index import (
    build_reviewer_snapshot,
    format_reviewer_snapshot_markdown,
    format_reviewer_snapshot_text,
)


def test_reviewer_snapshot_is_complete_for_current_incubator_package() -> None:
    snapshot = build_reviewer_snapshot(Path("."))

    assert snapshot["complete"] is True
    assert snapshot["section_present_total"] == snapshot["section_total"]
    assert snapshot["package_manifest_complete"] is True
    section_ids = {section["id"] for section in snapshot["sections"]}
    assert {
        "release_readiness",
        "package_manifest",
        "audit_pack",
        "schema_bundle",
        "example_matrix",
        "constraint_index",
        "smoke_suite",
    }.issubset(section_ids)


def test_reviewer_snapshot_text_and_markdown_are_human_readable() -> None:
    snapshot = build_reviewer_snapshot(Path("."))

    text = format_reviewer_snapshot_text(snapshot)
    markdown = format_reviewer_snapshot_markdown(snapshot)

    assert "Energy Aware Code Reviewer Snapshot" in text
    assert "Complete: True" in text
    assert "# Energy Aware Code Reviewer Snapshot" in markdown
    assert "## Reviewer sections" in markdown
    assert "Release readiness" in markdown
    assert "No shell" in markdown
