from __future__ import annotations

import argparse
import json
from pathlib import Path

from energy_core.decider import evaluate_candidate
from energy_core.evidence import read_evidence_records
from energy_core.ledger import append_decision
from energy_core.policy import load_policy
from energy_core.reporter import format_decision_markdown_report, format_decision_summary
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
    evaluate.add_argument("--decisions", required=True, type=Path)
    evaluate.add_argument("--format", choices=["json", "text"], default="text")
    evaluate.add_argument("--report", type=Path, help="Optional Markdown report path to write.")
    evaluate.add_argument(
        "--fail-on-non-accept",
        action="store_true",
        help="Return a non-zero exit code when the decision is not accept.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "evaluate":
        policy = load_policy(args.policy)
        candidate = read_candidate_state(args.candidate)
        evidence = read_evidence_records(args.evidence)
        decision = evaluate_candidate(policy=policy, candidate=candidate, evidence=evidence)
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

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
