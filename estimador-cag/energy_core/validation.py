from __future__ import annotations

from energy_core.models import CandidateState, EnergyPolicy

_REQUIRED_HARD_CONSTRAINTS = {
    "tests_failed",
    "compile_failed",
    "lint_failed",
    "secret_leak",
    "scope_creep",
    "missing_required_evidence",
    "unverified_success_claim",
}

_REQUIRED_EVIDENCE_TYPES = {
    "pytest_output",
    "compile_output",
    "lint_output",
    "secret_scan_output",
    "git_diff",
}


def validate_policy(policy: EnergyPolicy) -> dict[str, object]:
    """Return deterministic validation diagnostics for an energy policy."""

    missing: list[str] = []
    warnings: list[str] = []

    missing_hard_constraints = sorted(_REQUIRED_HARD_CONSTRAINTS - set(policy.hard_constraints))
    if missing_hard_constraints:
        missing.append("required_hard_constraints")

    missing_evidence_types = sorted(_REQUIRED_EVIDENCE_TYPES - set(policy.evidence_types))
    if missing_evidence_types:
        missing.append("required_evidence_types")

    unknown_acceptance_evidence = sorted(
        evidence_type
        for evidence_type in policy.required_acceptance_evidence
        if evidence_type not in policy.evidence_types
    )
    if unknown_acceptance_evidence:
        missing.append("known_required_acceptance_evidence")

    thresholds_valid = policy.thresholds.repair_min_soft_energy > policy.thresholds.accept_max_soft_energy
    if not thresholds_valid:
        missing.append("non_overlapping_soft_energy_thresholds")

    hard_constraints_without_repair_hint = sorted(
        constraint_id
        for constraint_id, constraint in policy.hard_constraints.items()
        if not constraint.repair_hint.strip()
    )
    if hard_constraints_without_repair_hint:
        warnings.append("hard_constraints_without_repair_hint")

    untrusted_acceptance_evidence = sorted(
        evidence_type
        for evidence_type in policy.required_acceptance_evidence
        if evidence_type in policy.evidence_types and not policy.evidence_types[evidence_type].trusted
    )
    if untrusted_acceptance_evidence:
        warnings.append("untrusted_required_acceptance_evidence")

    return {
        "policy_id": policy.policy_id,
        "version": policy.version,
        "complete": not missing,
        "missing": missing,
        "warnings": warnings,
        "hard_constraints": len(policy.hard_constraints),
        "soft_constraints": len(policy.soft_constraints),
        "evidence_types": len(policy.evidence_types),
        "decision_rules": len(policy.decision_rules),
        "required_acceptance_evidence": sorted(policy.required_acceptance_evidence),
        "missing_hard_constraints": missing_hard_constraints,
        "missing_evidence_types": missing_evidence_types,
        "unknown_acceptance_evidence": unknown_acceptance_evidence,
        "untrusted_acceptance_evidence": untrusted_acceptance_evidence,
        "thresholds_valid": thresholds_valid,
    }


def validate_candidate_state(policy: EnergyPolicy, candidate: CandidateState) -> dict[str, object]:
    """Return deterministic validation diagnostics for a candidate state."""

    missing: list[str] = []
    warnings: list[str] = []

    missing_artifacts = sorted(set(candidate.required_artifacts) - set(candidate.present_artifacts))
    if missing_artifacts:
        missing.append("required_artifacts_present")

    unknown_soft_flags = sorted(flag for flag in candidate.soft_flags if flag not in policy.soft_constraints)
    if unknown_soft_flags:
        missing.append("known_soft_flags")

    if candidate.validation_claims and not policy.required_acceptance_evidence:
        warnings.append("validation_claims_without_required_acceptance_evidence_policy")

    if not candidate.changed_files:
        warnings.append("no_changed_files_declared")

    return {
        "candidate_id": candidate.candidate_id,
        "spec_id": candidate.spec_id,
        "complete": not missing,
        "missing": missing,
        "warnings": warnings,
        "energy_before": candidate.energy_before,
        "changed_file_count": len(candidate.changed_files),
        "required_artifacts": sorted(candidate.required_artifacts),
        "present_artifacts": sorted(candidate.present_artifacts),
        "missing_artifacts": missing_artifacts,
        "soft_flags": sorted(candidate.soft_flags),
        "unknown_soft_flags": unknown_soft_flags,
        "validation_claims": sorted(candidate.validation_claims),
        "scope_claims": sorted(candidate.scope_claims),
    }
