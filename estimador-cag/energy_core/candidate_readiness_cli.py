from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from energy_core.candidate_readiness import (
    build_candidate_readiness_matrix,
    format_candidate_readiness_markdown,
    format_candidate_readiness_text,
)

DEFAULT_SPEC_DIR = Path(".energy/specs/0001-energy-policy-ledger")
DEFAULT_POLICY = DEFAULT_SPEC_DIR / "energy-policy.yaml"
DEFAULT_EVIDENCE = DEFAULT_SPEC_DIR / "evidence.jsonl"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report bundled candidate readiness without mutating the ledger."
    )
    parser.add_argument("--spec-dir", default=str(DEFAULT_SPEC_DIR))
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--evidence", default=str(DEFAULT_EVIDENCE))
    parser.add_argument("--format", choices=("text", "json", "markdown"), default="text")
    parser.add_argument("--fail-on-incomplete", action="store_true")
    args = parser.parse_args(argv)

    matrix = build_candidate_readiness_matrix(
        spec_dir=_resolve_path(Path(args.spec_dir)),
        policy_path=_resolve_path(Path(args.policy)),
        evidence_path=_resolve_path(Path(args.evidence)),
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
        return format_candidate_readiness_markdown(matrix)
    return format_candidate_readiness_text(matrix)


if __name__ == "__main__":
    raise SystemExit(main())
