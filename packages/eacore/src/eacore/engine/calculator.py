from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from eacore.contracts import (
    ConflictingIdentifierError,
    ConstraintObservation,
    EnergyComponent,
    EnergySnapshot,
    ObservationStatus,
)


def calculate_energy(
    *,
    snapshot_id: str,
    candidate_id: str,
    policy_ref: str,
    energy_before: float,
    observations: Sequence[ConstraintObservation],
    setup_work: bool = False,
    setup_work_justification: str | None = None,
) -> EnergySnapshot:
    by_id: dict[str, ConstraintObservation] = {}
    by_constraint: dict[str, list[ConstraintObservation]] = defaultdict(list)
    for observation in observations:
        existing = by_id.get(observation.observation_id)
        if existing is not None and existing != observation:
            raise ConflictingIdentifierError(
                f"observation id {observation.observation_id} reused with different content"
            )
        by_id[observation.observation_id] = observation
        by_constraint[observation.constraint_id].append(observation)

    components: list[EnergyComponent] = []
    hard: list[str] = []
    missing: list[str] = []
    conflicts: list[str] = []
    for constraint_id in sorted(by_constraint):
        group = by_constraint[constraint_id]
        penalty = sum(item.penalty for item in group)
        hard_blocking = any(item.hard_blocking for item in group)
        refs = tuple(sorted(item.observation_id for item in group))
        evidence = tuple(sorted({ref for item in group for ref in item.evidence_refs}))
        components.append(
            EnergyComponent(
                component_id=f"component:{constraint_id}",
                constraint_id=constraint_id,
                penalty=penalty,
                hard_blocking=hard_blocking,
                observation_refs=refs,
                evidence_refs=evidence,
            )
        )
        if hard_blocking:
            hard.extend(refs)
        missing.extend(
            item.observation_id
            for item in group
            if item.status == ObservationStatus.MISSING and item.required_evidence_missing
        )
        conflicts.extend(
            item.observation_id for item in group if item.status == ObservationStatus.CONFLICT
        )

    energy_after = sum(component.penalty for component in components)
    return EnergySnapshot(
        energy_snapshot_id=snapshot_id,
        candidate_id=candidate_id,
        policy_ref=policy_ref,
        energy_before=energy_before,
        energy_after=energy_after,
        energy_delta=energy_after - energy_before,
        hard_failure_refs=tuple(sorted(set(hard))),
        missing_evidence_refs=tuple(sorted(set(missing))),
        conflict_refs=tuple(sorted(set(conflicts))),
        components=tuple(components),
        setup_work=setup_work,
        setup_work_justification=setup_work_justification,
    )
