from __future__ import annotations

from pathlib import Path
from typing import Any

from energy_core.evidence import read_evidence_records
from energy_core.models import EvidenceRecord
from energy_core.policy import load_policy
from energy_core.state import read_candidate_state
from energy_core.validation import validate_candidate_state

MATRIX_VERSION = "1.0.0"

_EXPECTED_EXAMPLES = {
    "candidate_accept.json": {
        "expected_decision": "accept",
        "evidence_mode": "default",
    },
    "candidate_repair_missing_evidence.json": {
        "expected_decision": "repair",
        "evidence_mode": "empty",
    },
    "candidate_reject_tests_failed.json": {
        "expected_decision": "reject",
        "evidence_mode": "pytest_fail_only",
    },
    "candidate_reject_scope_creep.json": {
        "expected_decision": "reject",
        "evidence_mode": "default",
    },
}


def build_candidate_readiness_matrix(
    *,
    spec_dir: Path,
    policy_path: Path,
    evidence_path: Path,
) -> dict[str, Any]:
    policy = load_policy(policy_path)
    default_evidence = read_evidence_records(evidence_path)
    examples_dir = spec_dir / "examples"

    missing_examples: list[str] = []
    cases: list[dict[str, Any]] = []

    for filename, metadata in _EXPECTED_EXAMPLES.items():
        candidate_path = examples_dir / filename
        if not candidate_path.exists():
            missing_examples.append(str(candidate_path))
            continue

        candidate = read_candidate_state(candidate_path)
        candidate_validation = validate_candidate_state(policy, candidate)
        scenario_evidence = _scenario_evidence(
            filename=filename,
            default_evidence=default_evidence,
        )
        missing_evidence = _missing_required_evidence(
            required_evidence=policy.required_acceptance_evidence,
            evidence=scenario_evidence,
        )
        ready = bool(candidate_validation["complete"]) and not missing_evidence

        cases.append(
            {
                "example": filename,
                "candidate_id": candidate.candidate_id,
                "expected_decision": metadata["expected_decision"],
                "evidence_mode": metadata["evidence_mode"],
                "ready": ready,
                "candidate_complete": candidate_validation["complete"],
                "missing_artifacts": candidate_validation["missing_artifacts"],
                "missing_required_evidence": missing_evidence,
                "changed_file_count": candidate_validation["changed_file_count"],
                "required_artifact_count": len(candidate.required_artifacts),
                "present_artifact_count": len(candidate.present_artifacts),
                "evidence_record_count": len(scenario_evidence),
            }
        )

    incomplete_cases = [case for case in cases if not case["ready"]]
    complete = not missing_examples and len(cases) == len(_EXPECTED_EXAMPLES)

    return {
        "matrix_version": MATRIX_VERSION,
        "spec_dir": str(spec_dir),
        "complete": complete,
        "total_cases": len(cases),
        "expected_cases": len(_EXPECTED_EXAMPLES),
        "ready_cases": sum(1 for case in cases if case["ready"]),
        "not_ready_cases": len(incomplete_cases),
        "missing_examples": missing_examples,
        "cases": cases,
        "non_goals": [
            "Candidate readiness does not execute shell actions.",
            "Candidate readiness does not call LLM providers.",
            "Candidate readiness does not append to the decision ledger.",
            "Candidate readiness does not require every example to be ready.",
        ],
    }


def format_candidate_readiness_text(matrix: dict[str, Any]) -> str:
    lines = [
        "Energy Aware Code Candidate Readiness",
        f"Version: {matrix['matrix_version']}",
        f"Complete: {matrix['complete']}",
        f"Ready cases: {matrix['ready_cases']}/{matrix['total_cases']}",
        f"Not ready cases: {matrix['not_ready_cases']}",
    ]
    for case in matrix["cases"]:
        lines.append(
            f"- {case['example']}: ready={case['ready']}, "
            f"expected={case['expected_decision']}"
        )
    return "\n".join(lines)


def format_candidate_readiness_markdown(matrix: dict[str, Any]) -> str:
    lines = [
        "# Energy Aware Code Candidate Readiness",
        "",
        f"- Version: {matrix['matrix_version']}",
        f"- Complete: {matrix['complete']}",
        f"- Cases: {matrix['total_cases']}/{matrix['expected_cases']}",
        f"- Ready cases: {matrix['ready_cases']}/{matrix['total_cases']}",
        f"- Not ready cases: {matrix['not_ready_cases']}",
        "",
        "## Missing examples",
        "",
        *_bullet_list(matrix["missing_examples"]),
        "",
        "## Cases",
        "",
    ]
    for case in matrix["cases"]:
        lines.extend(_case_markdown(case))
    lines.extend(["", "## Non goals", ""])
    lines.extend(_bullet_list(matrix["non_goals"]))
    return "\n".join(lines)


def _scenario_evidence(
    *,
    filename: str,
    default_evidence: list[EvidenceRecord],
) -> list[EvidenceRecord]:
    if filename == "candidate_repair_missing_evidence.json":
        return []
    if filename == "candidate_reject_tests_failed.json":
        return [
            EvidenceRecord(
                evidence_id="candidate-readiness-pytest-failed",
                type="pytest_output",
                status="fail",
                summary="Candidate readiness models a failing pytest gate.",
                trusted=True,
                exit_code=1,
            )
        ]
    return list(default_evidence)


def _missing_required_evidence(
    *,
    required_evidence: list[str],
    evidence: list[EvidenceRecord],
) -> list[str]:
    trusted_pass_types = {
        record.type
        for record in evidence
        if record.trusted and record.status == "pass"
    }
    return sorted(set(required_evidence) - trusted_pass_types)


def _case_markdown(case: dict[str, Any]) -> list[str]:
    return [
        f"### {case['example']}",
        "",
        f"- Candidate: {case['candidate_id']}",
        f"- Expected decision: {case['expected_decision']}",
        f"- Evidence mode: {case['evidence_mode']}",
        f"- Ready: {case['ready']}",
        f"- Candidate complete: {case['candidate_complete']}",
        f"- Missing artifacts: {_inline_list(case['missing_artifacts'])}",
        f"- Missing required evidence: {_inline_list(case['missing_required_evidence'])}",
        f"- Changed files: {case['changed_file_count']}",
        f"- Required artifacts: {case['required_artifact_count']}",
        f"- Present artifacts: {case['present_artifact_count']}",
        f"- Evidence records: {case['evidence_record_count']}",
        "",
    ]


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]
