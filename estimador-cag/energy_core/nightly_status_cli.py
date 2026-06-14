from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from energy_core.nightly_status import (
    build_nightly_status,
    format_nightly_status_markdown,
    format_nightly_status_text,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a five-section EACODE nightly status pack."
    )
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--format", choices=("json", "text", "markdown"), default="text")
    parser.add_argument("--fail-on-incomplete", action="store_true")
    args = parser.parse_args(argv)

    status = build_nightly_status(args.project_root)
    print(_format(status, args.format))

    if args.fail_on_incomplete and not status["complete"]:
        return 1
    return 0


def _format(status: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(status, indent=2, sort_keys=True)
    if output_format == "markdown":
        return format_nightly_status_markdown(status)
    return format_nightly_status_text(status)


if __name__ == "__main__":
    raise SystemExit(main())
