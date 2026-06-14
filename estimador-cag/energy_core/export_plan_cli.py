from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from energy_core.export_plan import (
    build_export_plan,
    format_export_plan_markdown,
    format_export_plan_text,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a non-executing EACODE standalone export plan."
    )
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--format", choices=("json", "text", "markdown"), default="text")
    parser.add_argument("--fail-on-not-ready", action="store_true")
    args = parser.parse_args(argv)

    plan = build_export_plan(args.project_root)
    print(_format(plan, args.format))

    if args.fail_on_not_ready and not plan["ready"]:
        return 1
    return 0


def _format(plan: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(plan, indent=2, sort_keys=True)
    if output_format == "markdown":
        return format_export_plan_markdown(plan)
    return format_export_plan_text(plan)


if __name__ == "__main__":
    raise SystemExit(main())
