from __future__ import annotations

import argparse
import json
from pathlib import Path

from energy_core.release import (
    build_release_readiness,
    format_release_readiness_markdown,
    format_release_readiness_text,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build an Energy Aware Code release-readiness packet for future extraction."
    )
    parser.add_argument("--project-root", type=Path, default=_PROJECT_ROOT)
    parser.add_argument("--spec-dir", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--decisions", type=Path, help="Optional existing decision JSONL ledger path.")
    parser.add_argument("--format", choices=["json", "text", "markdown"], default="markdown")
    parser.add_argument("--report", type=Path, help="Optional Markdown report path to write.")
    parser.add_argument(
        "--fail-on-not-ready",
        action="store_true",
        help="Return exit code 1 when release readiness is blocked.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    project_root = _input_path(args.project_root)
    summary = build_release_readiness(
        project_root=project_root,
        spec_dir=_input_path(args.spec_dir),
        policy_path=_input_path(args.policy),
        candidate_path=_input_path(args.candidate),
        evidence_path=_input_path(args.evidence),
        decisions_path=_optional_input_path(args.decisions),
    )

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(format_release_readiness_markdown(summary), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(summary, indent=2, sort_keys=True))
    elif args.format == "text":
        print(format_release_readiness_text(summary))
    else:
        print(format_release_readiness_markdown(summary))

    if args.fail_on_not_ready and not summary["ready_to_extract"]:
        return 1
    return 0


def _input_path(path: Path) -> Path:
    if path.is_absolute() or path.exists():
        return path

    project_relative = _PROJECT_ROOT / path
    if project_relative.exists():
        return project_relative

    return path


def _optional_input_path(path: Path | None) -> Path | None:
    if path is None:
        return None
    return _input_path(path)


if __name__ == "__main__":
    raise SystemExit(main())
