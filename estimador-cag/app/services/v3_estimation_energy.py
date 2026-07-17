"""Deterministic energy, fingerprint and decision-ledger utilities for estimation V3."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence

from app.schemas.v3_energy import (
    ConstraintEnergySnapshot,
    ConstraintObservation,
    EstimateDecisionLedgerEntry,
    EstimateEnergyCard,
    RepairOutcome,
)

HARD_BLOCK_PENALTY = 10_000
MISSING_REQUIRED_EVIDENCE_PENALTY = 5_000
CONFLICT_PENALTY = 7_500


def candidate_fingerprint(payload: Mapping[str, object]) -> str:
    """Return a stable SHA-256 fingerprint for an allow-listed candidate projection."""

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def calculate_constraint_energy(
    *,
    candidate_id: str,
    policy_version: str,
    energy_before: int,
    observations: Iterable[ConstraintObservation],
) -> ConstraintEnergySnapshot:
    """Calculate deterministic energy; product policy remains the decision authority."""

    by_id: dict[str, ConstraintObservation] = {}
    for observation in observations:
        existing = by_id.get(observation.observation_id)
        if existing is not None and existing != observation:
            raise ValueError(f"conflicting observation ID: {observation.observation_id}")
        by_id[observation.observation_id] = observation

    hard_violations: list[str] = []
    missing_evidence: list[str] = []
    conflicts: list[str] = []
    soft_penalties: dict[str, int] = {}
    energy_after = 0
    evaluated = 0
    passing = 0

    for observation in sorted(by_id.values(), key=lambda item: item.observation_id):
        if observation.status != "not_applicable":
            evaluated += 1
        if observation.status == "pass":
            passing += 1
            continue
        if observation.status == "not_applicable":
            continue
        if observation.status == "missing":
            missing_evidence.append(observation.code)
            energy_after += MISSING_REQUIRED_EVIDENCE_PENALTY
        elif observation.status == "conflict":
            conflicts.append(observation.code)
            energy_after += CONFLICT_PENALTY
        elif observation.hard_blocking:
            hard_violations.append(observation.code)
            energy_after += HARD_BLOCK_PENALTY
        else:
            soft_penalties[observation.code] = observation.penalty
            energy_after += observation.penalty

    evidence_sufficiency = round(passing / evaluated, 4) if evaluated else 1.0
    snapshot_payload = {
        "candidate_id": candidate_id,
        "policy_version": policy_version,
        "energy_before": energy_before,
        "energy_after": energy_after,
        "hard_violations": hard_violations,
        "soft_penalties": soft_penalties,
        "missing_evidence": missing_evidence,
        "conflicts": conflicts,
    }
    snapshot_id = "energy:" + candidate_fingerprint(snapshot_payload)[:24]
    return ConstraintEnergySnapshot(
        snapshot_id=snapshot_id,
        candidate_id=candidate_id,
        policy_version=policy_version,
        energy_before=energy_before,
        energy_after=energy_after,
        energy_delta=energy_after - energy_before,
        hard_violations=hard_violations,
        soft_penalties=soft_penalties,
        missing_evidence=missing_evidence,
        conflicts=conflicts,
        evidence_sufficiency=evidence_sufficiency,
    )


def classify_repair(
    before: ConstraintEnergySnapshot,
    after: ConstraintEnergySnapshot,
    *,
    budget_exhausted: bool = False,
    repairable: bool = True,
) -> RepairOutcome:
    """Classify repair quality without allowing hard failures to hide behind lower energy."""

    if budget_exhausted:
        return "budget_exhausted"
    if not repairable:
        return "not_repairable"
    if after.hard_violations or after.missing_evidence or after.conflicts:
        return "no_improvement"
    if after.energy_after >= before.energy_after:
        return "no_improvement"
    return "improved"


def append_ledger_entries(
    current: Sequence[EstimateDecisionLedgerEntry],
    incoming: Sequence[EstimateDecisionLedgerEntry],
) -> list[EstimateDecisionLedgerEntry]:
    """Append immutable decisions idempotently and reject conflicting replay."""

    result = list(current)
    by_id = {entry.decision_id: entry for entry in result}
    if len(by_id) != len(result):
        raise ValueError("existing decision ledger contains duplicate IDs")
    for entry in incoming:
        existing = by_id.get(entry.decision_id)
        if existing is None:
            result.append(entry)
            by_id[entry.decision_id] = entry
        elif existing != entry:
            raise ValueError(f"conflicting decision ID: {entry.decision_id}")
    return result


def build_estimate_energy_card(
    *,
    snapshot: ConstraintEnergySnapshot,
    disposition: str,
    repairs: int,
    remaining_caveats: list[str] | None = None,
) -> EstimateEnergyCard:
    """Build a user-safe projection from authoritative deterministic state."""

    hard_constraints_passed = not (
        snapshot.hard_violations or snapshot.missing_evidence or snapshot.conflicts
    )
    return EstimateEnergyCard(
        candidate_id=snapshot.candidate_id,
        disposition=disposition,
        hard_constraints_passed=hard_constraints_passed,
        energy_before=snapshot.energy_before,
        energy_after=snapshot.energy_after,
        energy_delta=snapshot.energy_delta,
        evidence_sufficiency=snapshot.evidence_sufficiency,
        repairs=repairs,
        remaining_caveats=list(remaining_caveats or []),
        policy_version=snapshot.policy_version,
    )
