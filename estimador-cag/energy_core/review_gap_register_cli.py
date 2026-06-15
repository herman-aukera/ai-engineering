from __future__ import annotations

import argparse
import json
from pathlib import Path

from energy_core.review_gap_register import (
    build_review_gap_register,
    format_review_gap_register_markdown,
    format_review_gap_register_text,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an EACODE review gap register.")
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--format", choices=("text", "json", "markdown"), default="text")
    parser.add_argument("--fail-on-blocking", action="store_true")
    args = parser.parse_args()

    register = build_review_gap_register(args.project_root)
    if args.format == "json":
        print(json.dumps(register, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(format_review_gap_register_markdown(register))
    else:
        print(format_review_gap_register_text(register))

    if args.fail_on_blocking and register["blocking_gap_total"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
