from __future__ import annotations

from collections.abc import Iterable

from energy_core.critics import run_critics
from energy_core.models import CandidateState, EnergyDecision, EnergyPolicy, EvidenceRecord, Violation
from energy_core.scorer import hard_reject_ids, hard_repair_ids, missing_evidence_ids, soft_ids, total_energy


def evaluate_candidate(
    *, policy: EnergyPolicy, candidate: CandidateState, evidence: Iterable[EvidenceRecord]
) -> EnergyDecision:
    evidence_records = list(evidence)
    violations = run_critics(policy=policy, candidate=candidate, evidence=evidence_records)
    return decide(policy=policy, candidate=candidate, evidence=evidence_records, violations=violations)


def decide(
    *,
    policy: EnergyPolicy,
    candidate: CandidateState,
    evidence: list[EvidenceRecord],
    violations: list[Violation],
) -> EnergyDecision:
    hard_rejects = hard_reject_ids(violations)
    hard_repairs = hard_repair_ids(violations)
    soft_violations = soft_ids(violations)
    missing_evidence = missing_evidence_ids(violations)
    conflicts = [
        violation.violation_id for violation in violations if violation.constraint_type == "conflict"
    ]
    energy_after = total_energy(violations)
    energy_delta = energy_after - candidate.energy_before
    evidence_refs = [record.evidence_id for record in evidence]
    required_repairs = _required_repairs(violations)

    if hard_rejects:
        decision = "reject"
        reasoning_summary = "The candidate violates hard reject constraints."
        next_action = "repair_blocking_violations"
    elif conflicts:
        decision = "escalate"
        reasoning_summary = "Trusted evidence conflicts on a material decision."
        next_action = "human_review_required"
    elif hard_repairs or missing_evidence:
        decision = "repair"
        reasoning_summary = "The candidate is directionally valid but required repair evidence is missing or failed."
        next_action = "add_required_evidence" if missing_evidence else "repair_hard_constraints"
    elif _soft_energy(violations) > policy.thresholds.accept_max_soft_energy:
        decision = "repair"
        reasoning_summary = "Soft constraint energy exceeds the acceptance threshold."
        next_action = "repair_soft_constraints"
    else:
        decision = "accept"
        reasoning_summary = "Hard constraints pass, required evidence exists, and energy is below threshold."
        next_action = "stop"

    return EnergyDecision(
        policy_id=policy.policy_id,
        candidate_id=candidate.candidate_id,
        decision=decision,
        energy_before=candidate.energy_before,
        energy_after=energy_after,
        energy_delta=energy_delta,
        hard_reject_violations=hard_rejects,
        hard_repair_violations=hard_repairs,
        soft_violations=soft_violations,
        missing_evidence=missing_evidence,
        evidence_refs=evidence_refs,
        required_repairs=required_repairs,
        reasoning_summary=reasoning_summary,
        next_action=next_action,
    )


def _required_repairs(violations: list[Violation]) -> list[str]:
    repairs: list[str] = []
    for violation in violations:
        if violation.repair_hint not in repairs:
            repairs.append(violation.repair_hint)
    return repairs


def _soft_energy(violations: list[Violation]) -> int:
    return sum(violation.penalty for violation in violations if violation.constraint_type == "soft")
