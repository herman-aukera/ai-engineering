from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from energy_core.evidence_matrix import (
    build_evidence_matrix,
    format_evidence_matrix_markdown,
    format_evidence_matrix_text,
)

DEFAULT_SPEC_DIR = Path(".energy/specs/0001-energy-policy-ledger")
DEFAULT_POLICY = DEFAULT_SPEC_DIR / "energy-policy.yaml"
DEFAULT_EVIDENCE = DEFAULT_SPEC_DIR / "evidence.jsonl"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report evidence trust coverage.")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--evidence", default=str(DEFAULT_EVIDENCE))
    parser.add_argument("--format", choices=("text", "json", "markdown"), default="text")
    parser.add_argument("--fail-on-incomplete", action="store_true")
    args = parser.parse_args(argv)

    matrix = build_evidence_matrix(
        _resolve_path(Path(args.policy)),
        _resolve_path(Path(args.evidence)),
    )
    print(_format(matrix, args.format))

    if args.fail_on_incomplete and not matrix["complete"]:
        return 1
    return 0


def _resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    project_relative = PROJECT_ROOT / path
    if project_relative.exists():
        return project_relative
    return path


def _format(matrix: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(matrix, indent=2, sort_keys=True)
    if output_format == "markdown":
        return format_evidence_matrix_markdown(matrix)
    return format_evidence_matrix_text(matrix)


if __name__ == "__main__":
    raise SystemExit(main())
