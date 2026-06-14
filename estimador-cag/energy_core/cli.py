from __future__ import annotations

import argparse
import json
from pathlib import Path

from energy_core.decider import evaluate_candidate
from energy_core.evidence import EvidenceLoadError, read_evidence_records, summarize_evidence
from energy_core.ledger import append_decision
from energy_core.policy import load_policy
from energy_core.reporter import (
    format_decision_markdown_report,
    format_decision_summary,
    format_evidence_markdown_report,
    format_evidence_summary,
)
from energy_core.state import read_candidate_state

_DECISION_EXIT_CODES = {
    "accept": 0,
    "repair": 1,
    "reject": 2,
    "escalate": 3,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate an Energy Aware Code candidate state.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate = subparsers.add_parser("evaluate", help="Evaluate a candidate state against policy and evidence.")
    evaluate.add_argument("--policy", required=True, type=Path)
    evaluate.add_argument("--candidate", required=True, type=Path)
    evaluate.add_argument("--evidence", required=True, type=Path)
    evaluate.add_argument(
        "--decisions",
        type=Path,
        help="Decision JSONL ledger path. Required unless --dry-run is used.",
    )
    evaluate.add_argument("--format", choices=["json", "text"], default="text")
    evaluate.add_argument("--report", type=Path, help="Optional Markdown report path to write.")
    evaluate.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate without appending to the decision ledger.",
    )
    evaluate.add_argument(
        "--fail-on-non-accept",
        action="store_true",
        help="Return a non-zero exit code when the decision is not accept.",
    )

    evidence_summary = subparsers.add_parser(
        "evidence-summary",
        help="Summarize evidence quality without evaluating or appending a decision.",
    )
    evidence_summary.add_argument("--evidence", required=True, type=Path)
    evidence_summary.add_argument("--format", choices=["json", "text", "markdown"], default="text")
    evidence_summary.add_argument("--report", type=Path, help="Optional Markdown report path to write.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "evaluate":
            return _run_evaluate(args, parser)
        if args.command == "evidence-summary":
            return _run_evidence_summary(args)
    except EvidenceLoadError as exc:
        parser.exit(2, f"error: {exc}\n")

    parser.error(f"Unsupported command: {args.command}")
    return 2


def _run_evaluate(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.dry_run and args.decisions is None:
        parser.error("--decisions is required unless --dry-run is used.")

    policy = load_policy(args.policy)
    candidate = read_candidate_state(args.candidate)
    evidence = read_evidence_records(args.evidence)
    decision = evaluate_candidate(policy=policy, candidate=candidate, evidence=evidence)

    if not args.dry_run:
        append_decision(args.decisions, decision)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(format_decision_markdown_report(decision), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(decision.model_dump(mode="json"), indent=2, sort_keys=True))
    else:
        print(format_decision_summary(decision))

    if args.fail_on_non_accept:
        return _DECISION_EXIT_CODES[decision.decision]
    return 0


def _run_evidence_summary(args: argparse.Namespace) -> int:
    evidence = read_evidence_records(args.evidence)
    summary = summarize_evidence(evidence)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(format_evidence_markdown_report(summary), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(summary, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(format_evidence_markdown_report(summary))
    else:
        print(format_evidence_summary(summary))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
