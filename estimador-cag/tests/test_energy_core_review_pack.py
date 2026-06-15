from pathlib import Path

from energy_core.review_pack import build_review_pack, format_review_pack_markdown

EXPECTED_REVIEW_PACK_FILES = {
    "README.md",
    "reviewer_snapshot.md",
    "nightly_status.md",
    "release_readiness.md",
    "package_manifest.md",
    "export_plan.md",
    "command_catalog.md",
    "critic_coverage.md",
    "ledger_integrity.md",
    "candidate_readiness.md",
    "review_gap_register.md",
    "acceptance_trace.md",
    "demo_walkthrough.md",
}


def test_review_pack_writes_expected_artifacts(tmp_path: Path) -> None:
    summary = build_review_pack(Path("."), tmp_path / "review-pack")

    assert summary["complete"] is True
    assert summary["present_total"] == len(EXPECTED_REVIEW_PACK_FILES)
    filenames = {item["filename"] for item in summary["files"]}
    assert filenames == EXPECTED_REVIEW_PACK_FILES
    for item in summary["files"]:
        assert Path(item["path"]).is_file()
        assert item["size_bytes"] > 0


def test_review_pack_markdown_lists_outputs(tmp_path: Path) -> None:
    summary = build_review_pack(Path("."), tmp_path / "review-pack")
    markdown = format_review_pack_markdown(summary)

    assert "# Energy Aware Code Review Pack" in markdown
    assert "Complete: True" in markdown
    assert "reviewer_snapshot.md" in markdown
    assert "nightly_status.md" in markdown
    assert "package_manifest.md" in markdown
    assert "critic_coverage.md" in markdown
    assert "ledger_integrity.md" in markdown
    assert "candidate_readiness.md" in markdown
    assert "review_gap_register.md" in markdown
    assert "acceptance_trace.md" in markdown
    assert "demo_walkthrough.md" in markdown
