from __future__ import annotations

import argparse
import json
from pathlib import Path

from energy_core.examples import (
    build_example_matrix,
    format_example_matrix_markdown,
    format_example_matrix_text,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate bundled Energy Aware Code examples against expected decisions."
    )
    parser.add_argument("--spec-dir", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--format", choices=["json", "text", "markdown"], default="markdown")
    parser.add_argument("--report", type=Path, help="Optional Markdown report path to write.")
    parser.add_argument(
        "--fail-on-mismatch",
        action="store_true",
        help="Return exit code 1 when any example decision differs from its expected decision.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    matrix = build_example_matrix(
        spec_dir=_input_path(args.spec_dir),
        policy_path=_input_path(args.policy),
        evidence_path=_input_path(args.evidence),
    )

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(format_example_matrix_markdown(matrix), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(matrix, indent=2, sort_keys=True))
    elif args.format == "text":
        print(format_example_matrix_text(matrix))
    else:
        print(format_example_matrix_markdown(matrix))

    if args.fail_on_mismatch and not matrix["complete"]:
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
