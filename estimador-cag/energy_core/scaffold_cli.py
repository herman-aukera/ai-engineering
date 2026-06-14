from __future__ import annotations

import argparse
import json
from pathlib import Path

from energy_core.scaffold import (
    build_standalone_scaffold,
    format_standalone_scaffold_markdown,
    format_standalone_scaffold_text,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a standalone EACODE repository scaffold without copying source files."
    )
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--format", choices=["json", "markdown", "text"], default="text")
    parser.add_argument("--fail-on-incomplete", action="store_true")
    args = parser.parse_args(argv)

    scaffold = build_standalone_scaffold(args.project_root, args.output_dir)

    if args.format == "json":
        print(json.dumps(scaffold, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(format_standalone_scaffold_markdown(scaffold))
    else:
        print(format_standalone_scaffold_text(scaffold))

    if args.fail_on_incomplete and not scaffold["complete"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
