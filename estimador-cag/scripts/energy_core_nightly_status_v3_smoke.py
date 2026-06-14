from __future__ import annotations

from pathlib import Path

from energy_core.nightly_status import build_nightly_status, format_nightly_status_markdown


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]

    status = build_nightly_status(project_root)
    assert status["complete"] is True
    assert status["section_total"] == 5
    assert status["section_complete_total"] == 5

    markdown = format_nightly_status_markdown(status)
    assert "# Energy Aware Code Nightly Status" in markdown
    assert "M1 Policy health" in markdown
    assert "M2 Evidence completeness" in markdown
    assert "M3 Command safety surface" in markdown
    assert "M4 Release/export readiness" in markdown
    assert "M5 Maintainer handoff" in markdown

    print("Energy Core nightly status smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
