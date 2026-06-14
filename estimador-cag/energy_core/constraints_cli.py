from __future__ import annotations

import argparse
import json
from pathlib import Path

from energy_core.constraints import (
    build_constraint_index,
    format_constraint_index_markdown,
    format_constraint_index_text,
)
from energy_core.policy import load_policy

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render an Energy Aware Code constraint index.")
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--format", choices=["json", "text", "markdown"], default="text")
    parser.add_argument("--report", type=Path, help="Optional Markdown report path to write.")
    parser.add_argument(
        "--fail-on-incomplete",
        action="store_true",
        help="Return exit code 1 when the policy constraint index is incomplete.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    policy = load_policy(_input_path(args.policy))
    index = build_constraint_index(policy)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(format_constraint_index_markdown(index), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(index, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(format_constraint_index_markdown(index))
    else:
        print(format_constraint_index_text(index))

    if args.fail_on_incomplete and not index["complete"]:
        return 1
    return 0


def _input_path(path: Path) -> Path:
    if path.is_absolute() or path.exists():
        return path

    project_relative = _PROJECT_ROOT / path
    if project_relative.exists():
        return project_relative

    return path


if __name__ == "__main__":
    raise SystemExit(main())
