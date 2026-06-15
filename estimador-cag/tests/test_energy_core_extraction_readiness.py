from pathlib import Path

from energy_core.extraction_readiness import (
    build_extraction_readiness,
    format_extraction_readiness_markdown,
    format_extraction_readiness_text,
)


def test_extraction_readiness_is_complete_from_project_root() -> None:
    report = build_extraction_readiness(Path("."))

    assert report["complete"] is True
    assert report["complete_check_total"] == report["check_total"]
    assert report["blocking_gaps"] == 0
    assert report["incomplete_checks"] == []


def test_extraction_readiness_resolves_repository_root() -> None:
    report = build_extraction_readiness(Path(".."))

    assert report["complete"] is True
    assert report["project_root"].endswith("estimador-cag")


def test_extraction_readiness_formats_text_and_markdown() -> None:
    report = build_extraction_readiness(Path("."))

    text = format_extraction_readiness_text(report)
    markdown = format_extraction_readiness_markdown(report)

    assert "Energy Aware Code Extraction Readiness" in text
    assert "Complete: True" in text
    assert "# Energy Aware Code Extraction Readiness" in markdown
    assert "## Checks" in markdown
    assert "Package inventory" in markdown


def test_extraction_readiness_keeps_non_goals_explicit() -> None:
    report = build_extraction_readiness(Path("."))

    non_goals = " ".join(report["non_goals"])
    assert "does not create a standalone repository" in non_goals
    assert "does not copy files" in non_goals
    assert "does not execute shell actions" in non_goals
