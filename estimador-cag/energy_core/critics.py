from __future__ import annotations

from collections.abc import Iterable

from energy_core.models import (
    CandidateState,
    ConstraintPolicy,
    EnergyPolicy,
    EvidenceRecord,
    Violation,
)

_FAILED_EVIDENCE_TO_CONSTRAINT = {
    "pytest_output": "tests_failed",
    "compile_output": "compile_failed",
    "lint_output": "lint_failed",
    "secret_scan_output": "secret_leak",
}

_HARD_REJECT_IDS = {
    "tests_failed",
    "compile_failed",
    "secret_leak",
    "unsafe_command",
    "wrong_branch",
    "scope_creep",
    "leaked_proprietary_code",
    "executor_self_approved",
    "unverified_success_claim",
}

_HARD_REPAIR_IDS = {
    "missing_required_artifact",
    "missing_required_evidence",
    "missing_red_test_when_feasible",
    "missing_human_path",
    "missing_decision_record",
    "missing_energy_delta",
    "lint_failed",
}


def run_critics(
    *, policy: EnergyPolicy, candidate: CandidateState, evidence: Iterable[EvidenceRecord]
) -> list[Violation]:
    evidence_records = list(evidence)
    violations: list[Violation] = []
    violations.extend(_gate_critic(policy, evidence_records))
    violations.extend(_scope_critic(policy, candidate))
    violations.extend(_artifact_critic(policy, candidate))
    violations.extend(_claim_critic(policy, candidate, evidence_records))
    violations.extend(_evidence_critic(policy, evidence_records))
    violations.extend(_soft_critic(policy, candidate))
    return violations


def _constraint(policy: EnergyPolicy, violation_id: str) -> ConstraintPolicy | None:
    return policy.hard_constraints.get(violation_id) or policy.soft_constraints.get(violation_id)


def _violation(
    *,
    policy: EnergyPolicy,
    violation_id: str,
    critic: str,
    evidence: str,
    evidence_refs: list[str] | None = None,
) -> Violation:
    constraint = _constraint(policy, violation_id)
    if constraint is None:
        raise KeyError(f"Missing policy constraint for violation: {violation_id}")

    if violation_id in _HARD_REJECT_IDS or constraint.decision == "reject":
        constraint_type = "hard_reject"
    elif violation_id in _HARD_REPAIR_IDS or constraint.decision == "repair":
        constraint_type = "hard_repair"
    else:
        constraint_type = "soft"

    return Violation(
        violation_id=violation_id,
        critic=critic,
        constraint_type=constraint_type,
        penalty=constraint.penalty,
        evidence=evidence,
        repair_hint=constraint.repair_hint,
        evidence_refs=evidence_refs or [],
    )


def _gate_critic(policy: EnergyPolicy, evidence_records: list[EvidenceRecord]) -> list[Violation]:
    violations: list[Violation] = []
    for record in evidence_records:
        if record.status == "conflict":
            violations.append(
                Violation(
                    violation_id="conflicting_material_evidence",
                    critic="evidence_critic",
                    constraint_type="conflict",
                    penalty=900,
                    evidence=record.summary,
                    repair_hint="Escalate to human review because trusted evidence conflicts.",
                    evidence_refs=[record.evidence_id],
                )
            )
            continue

        if record.status != "fail":
            continue

        violation_id = _FAILED_EVIDENCE_TO_CONSTRAINT.get(record.type)
        if violation_id is None:
            continue

        violations.append(
            _violation(
                policy=policy,
                violation_id=violation_id,
                critic="gate_critic",
                evidence=record.summary,
                evidence_refs=[record.evidence_id],
            )
        )
    return violations


def _scope_critic(policy: EnergyPolicy, candidate: CandidateState) -> list[Violation]:
    scope_creep = "scope_creep" in candidate.scope_claims or any(
        path.startswith("estimador-cag/app/energy_chat/") or path.startswith("app/energy_chat/")
        for path in candidate.changed_files
    )
    if not scope_creep:
        return []

    return [
        _violation(
            policy=policy,
            violation_id="scope_creep",
            critic="scope_critic",
            evidence="Candidate changes files outside the approved Energy Aware Code Slice 1 scope.",
        )
    ]


def _artifact_critic(policy: EnergyPolicy, candidate: CandidateState) -> list[Violation]:
    missing = sorted(set(candidate.required_artifacts) - set(candidate.present_artifacts))
    if not missing:
        return []

    return [
        _violation(
            policy=policy,
            violation_id="missing_required_artifact",
            critic="artifact_critic",
            evidence="Missing required artifacts: " + ", ".join(missing),
        )
    ]


def _claim_critic(
    policy: EnergyPolicy, candidate: CandidateState, evidence_records: list[EvidenceRecord]
) -> list[Violation]:
    if "success_without_validation" not in candidate.validation_claims:
        return []
    has_validation_log = any(record.type == "validation_log" and record.status == "pass" for record in evidence_records)
    if has_validation_log:
        return []
    return [
        _violation(
            policy=policy,
            violation_id="unverified_success_claim",
            critic="claim_critic",
            evidence="Candidate claims success without validation evidence.",
        )
    ]


def _evidence_critic(policy: EnergyPolicy, evidence_records: list[EvidenceRecord]) -> list[Violation]:
    passing_evidence_types = {record.type for record in evidence_records if record.status == "pass"}
    missing = [
        evidence_type
        for evidence_type in policy.required_acceptance_evidence
        if evidence_type not in passing_evidence_types
    ]
    if not missing:
        return []

    return [
        _violation(
            policy=policy,
            violation_id="missing_required_evidence",
            critic="evidence_critic",
            evidence="Missing required acceptance evidence: " + ", ".join(missing),
        )
    ]


def _soft_critic(policy: EnergyPolicy, candidate: CandidateState) -> list[Violation]:
    violations: list[Violation] = []
    for flag in candidate.soft_flags:
        if flag not in policy.soft_constraints:
            continue
        violations.append(
            _violation(
                policy=policy,
                violation_id=flag,
                critic="maintainability_critic",
                evidence=f"Candidate reports soft quality flag: {flag}.",
            )
        )
    return violations
