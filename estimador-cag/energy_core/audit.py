from __future__ import annotations

from pathlib import Path
from typing import Any

from energy_core.bundle import build_bundle_manifest
from energy_core.decider import evaluate_candidate
from energy_core.evidence import read_evidence_records, summarize_evidence
from energy_core.ledger import read_decisions, summarize_decisions
from energy_core.policy import load_policy
from energy_core.specs import summarize_spec_package
from energy_core.state import read_candidate_state
from energy_core.trends import summarize_decision_trends
from energy_core.validation import validate_candidate_state, validate_policy


def build_audit_pack(
    *,
    spec_dir: Path,
    policy_path: Path,
    candidate_path: Path,
    evidence_path: Path,
    decisions_path: Path | None = None,
) -> dict[str, Any]:
    """Build a deterministic, JSON-compatible audit packet without mutating state."""

    policy = load_policy(policy_path)
    candidate = read_candidate_state(candidate_path)
    evidence = read_evidence_records(evidence_path)
    decision = evaluate_candidate(policy=policy, candidate=candidate, evidence=evidence)
    decisions = read_decisions(decisions_path) if decisions_path is not None else []
    existing_decisions_path = decisions_path if decisions_path is not None and decisions_path.exists() else None

    spec_coverage = summarize_spec_package(spec_dir)
    policy_validation = validate_policy(policy)
    candidate_validation = validate_candidate_state(policy, candidate)
    evidence_summary = summarize_evidence(evidence)
    ledger_summary = summarize_decisions(decisions)
    decision_trends = summarize_decision_trends(decisions)
    bundle_manifest = build_bundle_manifest(
        spec_dir=spec_dir,
        policy_path=policy_path,
        candidate_path=candidate_path,
        evidence_path=evidence_path,
        decisions_path=existing_decisions_path,
    )

    ready_to_accept = bool(
        spec_coverage["complete"]
        and policy_validation["complete"]
        and candidate_validation["complete"]
        and bundle_manifest["complete"]
        and decision.decision == "accept"
    )

    return {
        "complete": ready_to_accept,
        "ready_to_accept": ready_to_accept,
        "spec_dir": str(spec_dir),
        "policy_path": str(policy_path),
        "candidate_path": str(candidate_path),
        "evidence_path": str(evidence_path),
        "decisions_path": str(decisions_path) if decisions_path is not None else None,
        "spec_coverage": spec_coverage,
        "policy_validation": policy_validation,
        "candidate_validation": candidate_validation,
        "evidence_summary": evidence_summary,
        "decision": decision.model_dump(mode="json"),
        "ledger_summary": ledger_summary,
        "decision_trends": decision_trends,
        "bundle_manifest": bundle_manifest,
    }


def format_audit_pack_markdown(pack: dict[str, Any]) -> str:
    """Render an audit packet as a compact Markdown report for review."""

    decision = pack["decision"]
    spec = pack["spec_coverage"]
    policy = pack["policy_validation"]
    candidate = pack["candidate_validation"]
    evidence = pack["evidence_summary"]
    ledger = pack["ledger_summary"]
    trends = pack["decision_trends"]
    bundle = pack["bundle_manifest"]

    return "\n".join(
        [
            "# Energy Aware Code Audit Pack",
            "",
            f"- Ready to accept: {pack['ready_to_accept']}",
            f"- Spec complete: {spec['complete']}",
            f"- Policy complete: {policy['complete']}",
            f"- Candidate complete: {candidate['complete']}",
            f"- Bundle complete: {bundle['complete']}",
            f"- Decision preview: {decision['decision']}",
            f"- Energy after: {decision['energy_after']}",
            f"- Existing ledger decisions: {ledger['total']}",
            f"- Decision trend: {trends['trend']}",
            "",
            "## Paths",
            "",
            f"- Spec dir: {pack['spec_dir']}",
            f"- Policy: {pack['policy_path']}",
            f"- Candidate: {pack['candidate_path']}",
            f"- Evidence: {pack['evidence_path']}",
            f"- Decisions: {pack['decisions_path'] or 'none'}",
            "",
            "## Spec coverage",
            "",
            f"- Required present: {spec['present_required']}/{spec['total_required']}",
            f"- Missing: {_inline_list(spec['missing'])}",
            "",
            "## Policy validation",
            "",
            f"- Missing: {_inline_list(policy['missing'])}",
            f"- Warnings: {_inline_list(policy['warnings'])}",
            f"- Missing hard constraints: {_inline_list(policy['missing_hard_constraints'])}",
            f"- Missing evidence types: {_inline_list(policy['missing_evidence_types'])}",
            "",
            "## Candidate validation",
            "",
            f"- Missing: {_inline_list(candidate['missing'])}",
            f"- Warnings: {_inline_list(candidate['warnings'])}",
            f"- Missing artifacts: {_inline_list(candidate['missing_artifacts'])}",
            f"- Unknown soft flags: {_inline_list(candidate['unknown_soft_flags'])}",
            "",
            "## Evidence summary",
            "",
            f"- Total records: {evidence['total']}",
            f"- Trusted records: {evidence['trusted']}",
            f"- Failed evidence: {_inline_list(evidence['failed_evidence'])}",
            f"- Missing evidence: {_inline_list(evidence['missing_evidence'])}",
            f"- Conflicting evidence: {_inline_list(evidence['conflicting_evidence'])}",
            "",
            "## Decision preview",
            "",
            f"- Candidate: {decision['candidate_id']}",
            f"- Decision: {decision['decision']}",
            f"- Energy before: {decision['energy_before']}",
            f"- Energy after: {decision['energy_after']}",
            f"- Energy delta: {decision['energy_delta']}",
            f"- Hard reject: {_inline_list(decision['hard_reject_violations'])}",
            f"- Hard repair: {_inline_list(decision['hard_repair_violations'])}",
            f"- Missing evidence: {_inline_list(decision['missing_evidence'])}",
            f"- Next action: {decision['next_action']}",
            "",
            "## Ledger summary",
            "",
            f"- Total decisions: {ledger['total']}",
            f"- Accepted: {ledger['accepted']}",
            f"- Repair: {ledger['repair']}",
            f"- Reject: {ledger['reject']}",
            f"- Escalate: {ledger['escalate']}",
            "",
            "## Decision trends",
            "",
            f"- Trend: {trends['trend']}",
            f"- Non accept: {trends['non_accept']}",
            f"- Regressing steps: {trends['regressing']}",
            f"- Average energy after: {trends['average_energy_after']}",
            f"- Average energy delta: {trends['average_energy_delta']}",
            "",
            "## Bundle manifest",
            "",
            f"- Complete: {bundle['complete']}",
            f"- Present files: {bundle['present_files']}/{bundle['total_files']}",
            f"- Missing required: {_inline_list(bundle['missing_required'])}",
            "",
        ]
    )


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"
