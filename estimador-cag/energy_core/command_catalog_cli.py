from __future__ import annotations

import argparse
import json
from typing import Any

from energy_core.command_catalog import (
    build_command_catalog,
    format_command_catalog_markdown,
    format_command_catalog_text,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print the supported Energy Aware Code command catalog."
    )
    parser.add_argument(
        "--format",
        choices=["json", "text", "markdown"],
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--fail-on-incomplete",
        action="store_true",
        help="Exit nonzero if the command catalog is incomplete.",
    )
    args = parser.parse_args(argv)

    catalog = build_command_catalog()
    print(_format_catalog(catalog, args.format))

    if args.fail_on_incomplete and not catalog["complete"]:
        return 1
    return 0


def _format_catalog(catalog: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(catalog, indent=2, sort_keys=True)
    if output_format == "markdown":
        return format_command_catalog_markdown(catalog)
    return format_command_catalog_text(catalog)


if __name__ == "__main__":
    raise SystemExit(main())
