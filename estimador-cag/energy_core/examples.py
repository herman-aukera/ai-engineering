from __future__ import annotations

from pathlib import Path
from typing import Any

from energy_core.decider import evaluate_candidate
from energy_core.evidence import read_evidence_records
from energy_core.models import EnergyDecision, EvidenceRecord
from energy_core.policy import load_policy
from energy_core.state import read_candidate_state

_EXPECTED_DECISIONS = {
    "candidate_accept.json": "accept",
    "candidate_repair_missing_evidence.json": "repair",
    "candidate_reject_tests_failed.json": "reject",
    "candidate_reject_scope_creep.json": "reject",
}


class ExampleMatrixError(ValueError):
    """Raised when the example matrix cannot be built."""


def build_example_matrix(*, spec_dir: Path, policy_path: Path, evidence_path: Path) -> dict[str, Any]:
    policy = load_policy(policy_path)
    default_evidence = read_evidence_records(evidence_path)
    examples_dir = spec_dir / "examples"

    cases: list[dict[str, Any]] = []
    missing_examples: list[str] = []

    for filename, expected_decision in _EXPECTED_DECISIONS.items():
        candidate_path = examples_dir / filename
        if not candidate_path.exists():
            missing_examples.append(str(candidate_path))
            continue

        candidate = read_candidate_state(candidate_path)
        evidence = _evidence_for_example(filename, default_evidence)
        decision = evaluate_candidate(policy=policy, candidate=candidate, evidence=evidence)
        cases.append(_case_summary(filename, expected_decision, decision))

    mismatches = [case for case in cases if not case["passed"]]
    complete = not missing_examples and not mismatches and len(cases) == len(_EXPECTED_DECISIONS)

    return {
        "matrix_version": "1.0.0",
        "spec_dir": str(spec_dir),
        "complete": complete,
        "total_cases": len(cases),
        "expected_cases": len(_EXPECTED_DECISIONS),
        "passed_cases": sum(1 for case in cases if case["passed"]),
        "failed_cases": len(mismatches),
        "missing_examples": missing_examples,
        "mismatches": mismatches,
        "cases": cases,
    }


def format_example_matrix_text(matrix: dict[str, Any]) -> str:
    lines = [
        "Energy Aware Code Example Matrix",
        f"Complete: {matrix['complete']}",
        f"Passed cases: {matrix['passed_cases']}/{matrix['expected_cases']}",
        f"Failed cases: {matrix['failed_cases']}",
        f"Missing examples: {_inline_list(matrix['missing_examples'])}",
        "Cases:",
    ]
    lines.extend(
        f"- {case['example']}: expected={case['expected_decision']}, actual={case['actual_decision']}, passed={case['passed']}"
        for case in matrix["cases"]
    )
    return "\n".join(lines)


def format_example_matrix_markdown(matrix: dict[str, Any]) -> str:
    lines = [
        "# Energy Aware Code Example Matrix",
        "",
        f"- Complete: {matrix['complete']}",
        f"- Passed cases: {matrix['passed_cases']}/{matrix['expected_cases']}",
        f"- Failed cases: {matrix['failed_cases']}",
        "",
        "## Missing examples",
        "",
        *_bullet_list(matrix["missing_examples"]),
        "",
        "## Cases",
        "",
    ]
    for case in matrix["cases"]:
        lines.extend(
            [
                f"### {case['example']}",
                "",
                f"- Candidate: {case['candidate_id']}",
                f"- Expected decision: {case['expected_decision']}",
                f"- Actual decision: {case['actual_decision']}",
                f"- Passed: {case['passed']}",
                f"- Energy after: {case['energy_after']}",
                f"- Hard reject: {_inline_list(case['hard_reject_violations'])}",
                f"- Hard repair: {_inline_list(case['hard_repair_violations'])}",
                f"- Missing evidence: {_inline_list(case['missing_evidence'])}",
                "",
            ]
        )
    return "\n".join(lines)


def _evidence_for_example(filename: str, default_evidence: list[EvidenceRecord]) -> list[EvidenceRecord]:
    if filename == "candidate_repair_missing_evidence.json":
        return []
    if filename == "candidate_reject_tests_failed.json":
        return [
            EvidenceRecord(
                evidence_id="example-pytest-failed",
                type="pytest_output",
                status="fail",
                summary="Example matrix intentionally models a failing pytest gate.",
                trusted=True,
                exit_code=1,
            )
        ]
    return list(default_evidence)


def _case_summary(filename: str, expected_decision: str, decision: EnergyDecision) -> dict[str, Any]:
    return {
        "example": filename,
        "candidate_id": decision.candidate_id,
        "expected_decision": expected_decision,
        "actual_decision": decision.decision,
        "passed": decision.decision == expected_decision,
        "energy_after": decision.energy_after,
        "energy_delta": decision.energy_delta,
        "hard_reject_violations": decision.hard_reject_violations,
        "hard_repair_violations": decision.hard_repair_violations,
        "soft_violations": decision.soft_violations,
        "missing_evidence": decision.missing_evidence,
        "next_action": decision.next_action,
    }


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- {item}" for item in items]
