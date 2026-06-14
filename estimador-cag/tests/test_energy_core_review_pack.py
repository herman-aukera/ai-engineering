from pathlib import Path

from energy_core.review_pack import build_review_pack, format_review_pack_markdown


def test_review_pack_writes_expected_artifacts(tmp_path: Path) -> None:
    summary = build_review_pack(Path("."), tmp_path / "review-pack")

    assert summary["complete"] is True
    assert summary["present_total"] == 8
    filenames = {item["filename"] for item in summary["files"]}
    assert filenames == {
        "README.md",
        "reviewer_snapshot.md",
        "release_readiness.md",
        "package_manifest.md",
        "export_plan.md",
        "command_catalog.md",
        "critic_coverage.md",
        "ledger_integrity.md",
    }
    for item in summary["files"]:
        assert Path(item["path"]).is_file()
        assert item["size_bytes"] > 0


def test_review_pack_markdown_lists_outputs(tmp_path: Path) -> None:
    summary = build_review_pack(Path("."), tmp_path / "review-pack")
    markdown = format_review_pack_markdown(summary)

    assert "# Energy Aware Code Review Pack" in markdown
    assert "Complete: True" in markdown
    assert "reviewer_snapshot.md" in markdown
    assert "package_manifest.md" in markdown
    assert "critic_coverage.md" in markdown
    assert "ledger_integrity.md" in markdown
