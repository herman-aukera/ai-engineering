from __future__ import annotations

import argparse
import json
from pathlib import Path

from energy_core.critic_coverage import (
    build_critic_coverage,
    format_critic_coverage_markdown,
    format_critic_coverage_text,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.exists():
        return candidate
    project_candidate = _project_root() / path
    if project_candidate.exists():
        return project_candidate
    return candidate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report deterministic critic coverage for policy constraints."
    )
    parser.add_argument(
        "--policy",
        default=".energy/specs/0001-energy-policy-ledger/energy-policy.yaml",
        help="Energy policy path.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json", "markdown"),
        default="text",
    )
    parser.add_argument(
        "--fail-on-unclassified",
        action="store_true",
        help="Exit non-zero if any policy constraint is not classified.",
    )
    args = parser.parse_args(argv)

    coverage = build_critic_coverage(_resolve_path(args.policy))

    if args.format == "json":
        print(json.dumps(coverage, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(format_critic_coverage_markdown(coverage))
    else:
        print(format_critic_coverage_text(coverage))

    if args.fail_on_unclassified and not coverage["complete"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
