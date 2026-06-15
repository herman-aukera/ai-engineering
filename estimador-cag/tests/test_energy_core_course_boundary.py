from __future__ import annotations

from pathlib import Path

from energy_core.course_boundary import (
    build_course_boundary_report,
    format_course_boundary_markdown,
)


def test_course_boundary_report_marks_eacode_as_incubator() -> None:
    report = build_course_boundary_report(Path("."))

    assert report["complete"] is True
    assert report["active_product"] == "EACODE"
    assert report["branch_role"] == "long-lived incubator"
    assert report["blocking_conflicts"] == []


def test_course_boundary_lists_coursework_and_product_boundaries() -> None:
    report = build_course_boundary_report(Path("."))
    boundary_ids = {item["id"] for item in report["boundaries"]}

    assert "session08_pgvector" in boundary_ids
    assert "session09_evaluation_quality" in boundary_ids
    assert "eachat_boundary" in boundary_ids
    assert "finalproject_boundary" in boundary_ids


def test_course_boundary_markdown_is_reviewer_readable() -> None:
    report = build_course_boundary_report(Path("."))
    markdown = format_course_boundary_markdown(report)

    assert "# Energy Aware Code Course Boundary" in markdown
    assert "Session 09 evaluation-quality work belongs" in markdown
    assert "Course boundary report does not execute shell actions" in markdown
