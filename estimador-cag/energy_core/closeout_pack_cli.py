from __future__ import annotations

import argparse
import json
from pathlib import Path

from energy_core.closeout_pack import (
    build_closeout_pack,
    format_closeout_pack_markdown,
    format_closeout_pack_text,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an EACODE closeout pack report.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--format", choices=("text", "json", "markdown"), default="text")
    parser.add_argument("--fail-on-incomplete", action="store_true")
    args = parser.parse_args()

    report = build_closeout_pack(Path(args.project_root))

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(format_closeout_pack_markdown(report))
    else:
        print(format_closeout_pack_text(report))

    if args.fail_on_incomplete and not report["complete"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
