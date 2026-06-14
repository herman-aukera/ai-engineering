from __future__ import annotations

import argparse
from pathlib import Path

from energy_core.review_pack import (
    build_review_pack,
    format_review_pack_markdown,
    format_review_pack_text,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export a deterministic EACODE reviewer artifact pack."
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--format", choices=["text", "markdown"], default="text")
    parser.add_argument("--fail-on-incomplete", action="store_true")
    args = parser.parse_args(argv)

    summary = build_review_pack(
        project_root=Path(args.project_root),
        output_dir=Path(args.output_dir),
    )
    if args.format == "markdown":
        print(format_review_pack_markdown(summary))
    else:
        print(format_review_pack_text(summary))

    if args.fail_on_incomplete and not summary["complete"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
