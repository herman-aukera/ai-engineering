from __future__ import annotations

import argparse
import json
from pathlib import Path

from energy_core.package_manifest import (
    build_package_manifest,
    format_package_manifest_markdown,
    format_package_manifest_text,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build an Energy Aware Code package manifest for future extraction."
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
        help="Return exit code 1 when required package artifacts are missing.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    manifest = build_package_manifest(args.project_root)

    if args.format == "json":
        print(json.dumps(manifest, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(format_package_manifest_markdown(manifest))
    else:
        print(format_package_manifest_text(manifest))

    if args.fail_on_incomplete and not manifest["complete"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
