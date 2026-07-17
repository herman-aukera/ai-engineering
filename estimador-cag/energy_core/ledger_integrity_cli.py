from __future__ import annotations

import argparse
import json
from pathlib import Path

from energy_core.ledger_integrity import (
    build_ledger_integrity,
    format_ledger_integrity_markdown,
    format_ledger_integrity_text,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = Path(".energy/specs/0001-energy-policy-ledger/decisions.jsonl")
DEFAULT_EVIDENCE = Path(".energy/specs/0001-energy-policy-ledger/evidence.jsonl")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect Energy Core decision ledger integrity without mutation."
    )
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    parser.add_argument(
        "--evidence",
        default=str(DEFAULT_EVIDENCE),
        help="Evidence JSONL used to validate decision evidence references.",
    )
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    parser.add_argument(
        "--fail-on-invalid",
        action="store_true",
        help="Exit non-zero when the ledger is missing or has invalid records.",
    )
    args = parser.parse_args(argv)

    report = build_ledger_integrity(
        _resolve_path(args.ledger),
        evidence_path=_resolve_path(args.evidence),
    )

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(format_ledger_integrity_markdown(report))
    else:
        print(format_ledger_integrity_text(report))

    if args.fail_on_invalid and not report["complete"]:
        return 1
    return 0


def _resolve_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    if path.exists():
        return path.resolve()
    project_candidate = PROJECT_ROOT / path
    if project_candidate.exists() or path.parts[:1] == (".energy",):
        return project_candidate
    return path.resolve()


if __name__ == "__main__":
    raise SystemExit(main())
