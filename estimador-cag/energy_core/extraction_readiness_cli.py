from __future__ import annotations

import argparse
from pathlib import Path

from energy_core.extraction_readiness import (
    build_extraction_readiness,
    format_extraction_readiness_markdown,
    format_extraction_readiness_text,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render Energy Aware Code extraction readiness."
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Path to estimador-cag or repository root.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "markdown"),
        default="text",
    )
    parser.add_argument(
        "--fail-on-incomplete",
        action="store_true",
        help="Exit non-zero when extraction readiness is incomplete.",
    )
    args = parser.parse_args(argv)

    report = build_extraction_readiness(Path(args.project_root))
    if args.format == "markdown":
        print(format_extraction_readiness_markdown(report))
    else:
        print(format_extraction_readiness_text(report))

    if args.fail_on_incomplete and not report["complete"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
