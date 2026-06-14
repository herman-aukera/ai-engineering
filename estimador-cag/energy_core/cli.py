from __future__ import annotations

import argparse
import json
from pathlib import Path

from energy_core.audit import build_audit_pack, format_audit_pack_markdown
from energy_core.bundle import (
    build_bundle_manifest,
    format_bundle_manifest_markdown,
    format_bundle_manifest_text,
)
from energy_core.decider import evaluate_candidate
from energy_core.evidence import EvidenceLoadError, read_evidence_records, summarize_evidence
from energy_core.ledger import LedgerLoadError, append_decision, read_decisions, summarize_decisions
from energy_core.policy import load_policy
from energy_core.reporter import (
    format_decision_markdown_report,
    format_decision_summary,
    format_evidence_markdown_report,
    format_evidence_summary,
    format_ledger_markdown_report,
    format_ledger_summary,
    format_spec_coverage_markdown_report,
    format_spec_coverage_summary,
)
from energy_core.specs import summarize_spec_package
from energy_core.state import read_candidate_state
from energy_core.trends import (
    format_decision_trends_markdown,
    format_decision_trends_text,
    summarize_decision_trends,
)
from energy_core.validation import validate_candidate_state, validate_policy
from energy_core.validation_reporter import (
    format_candidate_validation_markdown_report,
    format_candidate_validation_summary,
    format_policy_validation_markdown_report,
    format_policy_validation_summary,
)

_DECISION_EXIT_CODES = {
    "accept": 0,
    "repair": 1,
    "reject": 2,
    "escalate": 3,
}
_PROJECT_ROOT = Path(__file__).resolve().parents[1]


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

    policy_validate = subparsers.add_parser(
        "policy-validate",
        help="Validate an Energy Aware Code policy before evaluating candidates.",
    )
    policy_validate.add_argument("--policy", required=True, type=Path)
    policy_validate.add_argument("--format", choices=["json", "text", "markdown"], default="text")
    policy_validate.add_argument("--report", type=Path, help="Optional Markdown report path to write.")
    policy_validate.add_argument(
        "--fail-on-invalid",
        action="store_true",
        help="Return exit code 1 when the policy contract is incomplete.",
    )

    candidate_validate = subparsers.add_parser(
        "candidate-validate",
        help="Validate a candidate state against the active policy before evaluation.",
    )
    candidate_validate.add_argument("--policy", required=True, type=Path)
    candidate_validate.add_argument("--candidate", required=True, type=Path)
    candidate_validate.add_argument("--format", choices=["json", "text", "markdown"], default="text")
    candidate_validate.add_argument("--report", type=Path, help="Optional Markdown report path to write.")
    candidate_validate.add_argument(
        "--fail-on-invalid",
        action="store_true",
        help="Return exit code 1 when the candidate contract is incomplete.",
    )

    evidence_summary = subparsers.add_parser(
        "evidence-summary",
        help="Summarize evidence quality without evaluating or appending a decision.",
    )
    evidence_summary.add_argument("--evidence", required=True, type=Path)
    evidence_summary.add_argument("--format", choices=["json", "text", "markdown"], default="text")
    evidence_summary.add_argument("--report", type=Path, help="Optional Markdown report path to write.")

    ledger_summary = subparsers.add_parser(
        "ledger-summary",
        help="Summarize the append-only decision ledger without mutating it.",
    )
    ledger_summary.add_argument("--decisions", required=True, type=Path)
    ledger_summary.add_argument("--format", choices=["json", "text", "markdown"], default="text")
    ledger_summary.add_argument("--report", type=Path, help="Optional Markdown report path to write.")

    decision_trends = subparsers.add_parser(
        "decision-trends",
        help="Summarize energy and decision trends from the append-only ledger.",
    )
    decision_trends.add_argument("--decisions", required=True, type=Path)
    decision_trends.add_argument("--format", choices=["json", "text", "markdown"], default="text")
    decision_trends.add_argument("--report", type=Path, help="Optional Markdown report path to write.")
    decision_trends.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Return exit code 1 when the trend summary contains regressing steps.",
    )

    spec_coverage = subparsers.add_parser(
        "spec-coverage",
        help="Summarize required files and examples in an Energy Aware Code spec package.",
    )
    spec_coverage.add_argument("--spec-dir", required=True, type=Path)
    spec_coverage.add_argument("--format", choices=["json", "text", "markdown"], default="text")
    spec_coverage.add_argument("--report", type=Path, help="Optional Markdown report path to write.")
    spec_coverage.add_argument(
        "--fail-on-incomplete",
        action="store_true",
        help="Return exit code 1 when required spec artifacts are missing.",
    )

    bundle_manifest = subparsers.add_parser(
        "bundle-manifest",
        help="Build a portable review-bundle manifest with file hashes and no file contents.",
    )
    bundle_manifest.add_argument("--spec-dir", required=True, type=Path)
    bundle_manifest.add_argument("--policy", required=True, type=Path)
    bundle_manifest.add_argument("--candidate", required=True, type=Path)
    bundle_manifest.add_argument("--evidence", required=True, type=Path)
    bundle_manifest.add_argument("--decisions", type=Path, help="Optional existing decision JSONL ledger path.")
    bundle_manifest.add_argument("--format", choices=["json", "text", "markdown"], default="markdown")
    bundle_manifest.add_argument("--report", type=Path, help="Optional Markdown report path to write.")
    bundle_manifest.add_argument(
        "--fail-on-incomplete",
        action="store_true",
        help="Return exit code 1 when required bundle files are missing.",
    )

    audit_pack = subparsers.add_parser(
        "audit-pack",
        help="Build one deterministic audit packet before handing a candidate to a human reviewer.",
    )
    audit_pack.add_argument("--spec-dir", required=True, type=Path)
    audit_pack.add_argument("--policy", required=True, type=Path)
    audit_pack.add_argument("--candidate", required=True, type=Path)
    audit_pack.add_argument("--evidence", required=True, type=Path)
    audit_pack.add_argument("--decisions", type=Path, help="Optional existing decision JSONL ledger path.")
    audit_pack.add_argument("--format", choices=["json", "markdown"], default="markdown")
    audit_pack.add_argument("--report", type=Path, help="Optional Markdown report path to write.")
    audit_pack.add_argument(
        "--fail-on-not-ready",
        action="store_true",
        help="Return exit code 1 when the audit packet is not ready to accept.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "evaluate":
            return _run_evaluate(args, parser)
        if args.command == "policy-validate":
            return _run_policy_validate(args)
        if args.command == "candidate-validate":
            return _run_candidate_validate(args)
        if args.command == "evidence-summary":
            return _run_evidence_summary(args)
        if args.command == "ledger-summary":
            return _run_ledger_summary(args)
        if args.command == "decision-trends":
            return _run_decision_trends(args)
        if args.command == "spec-coverage":
            return _run_spec_coverage(args)
        if args.command == "bundle-manifest":
            return _run_bundle_manifest(args)
        if args.command == "audit-pack":
            return _run_audit_pack(args)
    except EvidenceLoadError as exc:
        parser.exit(2, f"error: {exc}\n")
    except LedgerLoadError as exc:
        parser.exit(2, f"error: {exc}\n")

    parser.error(f"Unsupported command: {args.command}")
    return 2


def _run_evaluate(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.dry_run and args.decisions is None:
        parser.error("--decisions is required unless --dry-run is used.")

    policy = load_policy(_input_path(args.policy))
    candidate = read_candidate_state(_input_path(args.candidate))
    evidence = read_evidence_records(_input_path(args.evidence))
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


def _run_policy_validate(args: argparse.Namespace) -> int:
    policy = load_policy(_input_path(args.policy))
    summary = validate_policy(policy)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(format_policy_validation_markdown_report(summary), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(summary, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(format_policy_validation_markdown_report(summary))
    else:
        print(format_policy_validation_summary(summary))

    if args.fail_on_invalid and not summary["complete"]:
        return 1
    return 0


def _run_candidate_validate(args: argparse.Namespace) -> int:
    policy = load_policy(_input_path(args.policy))
    candidate = read_candidate_state(_input_path(args.candidate))
    summary = validate_candidate_state(policy, candidate)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(format_candidate_validation_markdown_report(summary), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(summary, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(format_candidate_validation_markdown_report(summary))
    else:
        print(format_candidate_validation_summary(summary))

    if args.fail_on_invalid and not summary["complete"]:
        return 1
    return 0


def _run_evidence_summary(args: argparse.Namespace) -> int:
    evidence = read_evidence_records(_input_path(args.evidence))
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


def _run_ledger_summary(args: argparse.Namespace) -> int:
    decisions = read_decisions(_input_path(args.decisions))
    summary = summarize_decisions(decisions)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(format_ledger_markdown_report(summary), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(summary, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(format_ledger_markdown_report(summary))
    else:
        print(format_ledger_summary(summary))

    return 0


def _run_decision_trends(args: argparse.Namespace) -> int:
    decisions = read_decisions(_input_path(args.decisions))
    summary = summarize_decision_trends(decisions)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(format_decision_trends_markdown(summary), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(summary, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(format_decision_trends_markdown(summary))
    else:
        print(format_decision_trends_text(summary))

    if args.fail_on_regression and summary["regressing"]:
        return 1
    return 0


def _run_spec_coverage(args: argparse.Namespace) -> int:
    summary = summarize_spec_package(_input_path(args.spec_dir))

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(format_spec_coverage_markdown_report(summary), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(summary, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(format_spec_coverage_markdown_report(summary))
    else:
        print(format_spec_coverage_summary(summary))

    if args.fail_on_incomplete and not summary["complete"]:
        return 1
    return 0


def _run_bundle_manifest(args: argparse.Namespace) -> int:
    manifest = build_bundle_manifest(
        spec_dir=_input_path(args.spec_dir),
        policy_path=_input_path(args.policy),
        candidate_path=_input_path(args.candidate),
        evidence_path=_input_path(args.evidence),
        decisions_path=_optional_input_path(args.decisions),
    )

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(format_bundle_manifest_markdown(manifest), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(manifest, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(format_bundle_manifest_markdown(manifest))
    else:
        print(format_bundle_manifest_text(manifest))

    if args.fail_on_incomplete and not manifest["complete"]:
        return 1
    return 0


def _run_audit_pack(args: argparse.Namespace) -> int:
    pack = build_audit_pack(
        spec_dir=_input_path(args.spec_dir),
        policy_path=_input_path(args.policy),
        candidate_path=_input_path(args.candidate),
        evidence_path=_input_path(args.evidence),
        decisions_path=_optional_input_path(args.decisions),
    )

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(format_audit_pack_markdown(pack), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(pack, indent=2, sort_keys=True))
    else:
        print(format_audit_pack_markdown(pack))

    if args.fail_on_not_ready and not pack["ready_to_accept"]:
        return 1
    return 0


def _input_path(path: Path) -> Path:
    """Resolve package-local inputs from either project root or repository root."""

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
