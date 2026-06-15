from __future__ import annotations

import argparse
import json
from pathlib import Path

from energy_core.surface_consistency import (
    build_surface_consistency,
    format_surface_consistency_markdown,
    format_surface_consistency_text,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit reviewer surface consistency.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    parser.add_argument("--fail-on-incomplete", action="store_true")
    args = parser.parse_args()

    report = build_surface_consistency(Path(args.project_root))
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(format_surface_consistency_markdown(report))
    else:
        print(format_surface_consistency_text(report))

    if args.fail_on_incomplete and not report["complete"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
