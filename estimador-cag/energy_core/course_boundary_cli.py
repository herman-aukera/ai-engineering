from __future__ import annotations

import argparse
import json
from pathlib import Path

from energy_core.course_boundary import (
    build_course_boundary_report,
    format_course_boundary_markdown,
    format_course_boundary_text,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report EACODE boundaries against coursework branches."
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--format", choices=["text", "markdown", "json"], default="text")
    parser.add_argument("--fail-on-conflict", action="store_true")
    args = parser.parse_args()

    report = build_course_boundary_report(Path(args.project_root))

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(format_course_boundary_markdown(report))
    else:
        print(format_course_boundary_text(report))

    if args.fail_on_conflict and report["blocking_conflicts"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
