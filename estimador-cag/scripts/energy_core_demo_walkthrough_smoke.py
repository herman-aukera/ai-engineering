from __future__ import annotations

from pathlib import Path

from energy_core.demo_walkthrough import (
    build_demo_walkthrough,
    format_demo_walkthrough_markdown,
)


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    report = build_demo_walkthrough(project_root)
    markdown = format_demo_walkthrough_markdown(report)

    if not report["complete"]:
        raise AssertionError("Demo walkthrough is incomplete.")
    if "# Energy Aware Code Demo Walkthrough" not in markdown:
        raise AssertionError("Demo walkthrough heading is missing.")
    if "Step 5" not in markdown:
        raise AssertionError("Demo walkthrough does not list all expected steps.")

    print("Energy Core demo walkthrough smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
