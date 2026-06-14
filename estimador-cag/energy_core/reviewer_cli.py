from __future__ import annotations

import argparse
import json
from pathlib import Path

from energy_core.reviewer_index import (
    build_reviewer_snapshot,
    format_reviewer_snapshot_markdown,
    format_reviewer_snapshot_text,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build an Energy Aware Code reviewer snapshot index."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
        help="Path to estimador-cag or the repository root containing it.",
    )
    parser.add_argument("--format", choices=["json", "markdown", "text"], default="json")
    parser.add_argument(
        "--fail-on-incomplete",
        action="store_true",
        help="Return exit code 1 when the snapshot is incomplete.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    snapshot = build_reviewer_snapshot(args.project_root)

    if args.format == "json":
        print(json.dumps(snapshot, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(format_reviewer_snapshot_markdown(snapshot))
    else:
        print(format_reviewer_snapshot_text(snapshot))

    if args.fail_on_incomplete and not snapshot["complete"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
