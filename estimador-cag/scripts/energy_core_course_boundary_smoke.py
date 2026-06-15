from __future__ import annotations

from pathlib import Path

from energy_core.course_boundary import (
    build_course_boundary_report,
    format_course_boundary_text,
)


def main() -> int:
    report = build_course_boundary_report(Path(__file__).resolve().parents[1])
    text = format_course_boundary_text(report)
    print(text)
    assert report["complete"] is True
    assert not report["blocking_conflicts"]
    assert "EACODE" in text
    print("Energy Core course boundary smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
