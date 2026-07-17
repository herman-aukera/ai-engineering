from __future__ import annotations

from eacore.contracts import (
    DecisionEnvelope,
    EnergySnapshot,
    OutcomeClass,
    RepairRef,
    RepairResult,
    TransitionInvariantError,
)


def verify_transition(
    *,
    decision: DecisionEnvelope,
    energy: EnergySnapshot,
    previous_fingerprint: str | None = None,
    candidate_fingerprint: str | None = None,
    repair: RepairRef | None = None,
) -> None:
    if decision.candidate_id != energy.candidate_id:
        raise TransitionInvariantError("decision and energy snapshot target different candidates")

    if decision.outcome_class == OutcomeClass.ACCEPTED:
        if energy.hard_failure_refs:
            raise TransitionInvariantError("hard blockers cannot produce accepted")
        if energy.missing_evidence_refs:
            raise TransitionInvariantError("required missing evidence cannot produce accepted")
        if energy.conflict_refs:
            raise TransitionInvariantError("material conflict cannot produce accepted")
        if energy.energy_delta >= 0 and not energy.setup_work:
            raise TransitionInvariantError(
                "accepted requires negative energy delta or explicit bounded setup work"
            )

    if (
        previous_fingerprint is not None
        and candidate_fingerprint is not None
        and previous_fingerprint == candidate_fingerprint
        and repair is not None
    ):
        raise TransitionInvariantError("repeated candidate fingerprint cannot be a new repair")

    if repair is not None and repair.result == RepairResult.IMPROVED and energy.energy_delta >= 0:
        raise TransitionInvariantError("zero or positive repair delta cannot be marked improved")

    if decision.outcome_class == OutcomeClass.ACCEPTED and decision.authorization_ref is None:
        raise TransitionInvariantError(
            "accepted outcome requires independent authorization reference"
        )
