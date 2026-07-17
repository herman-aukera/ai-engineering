import pytest

from eacore.contracts import ConflictingIdentifierError, ConstraintObservation, ObservationStatus
from eacore.engine import calculate_energy


def observation(
    oid: str,
    constraint: str,
    status: ObservationStatus,
    penalty: float,
    *,
    hard: bool = False,
    required_missing: bool = False,
) -> ConstraintObservation:
    return ConstraintObservation(
        observation_id=oid,
        constraint_id=constraint,
        status=status,
        penalty=penalty,
        hard_blocking=hard,
        required_evidence_missing=required_missing,
        summary=oid,
    )


def test_energy_sums_by_constraint_and_uses_after_minus_before() -> None:
    snapshot = calculate_energy(
        snapshot_id="energy:1",
        candidate_id="candidate:1",
        policy_ref="policy:1",
        energy_before=20,
        observations=(
            observation("o1", "grounding", ObservationStatus.FAIL, 4),
            observation("o2", "grounding", ObservationStatus.FAIL, 3),
            observation("o3", "clarity", ObservationStatus.FAIL, 2),
        ),
    )
    assert snapshot.energy_after == 9
    assert snapshot.energy_delta == -11
    assert [item.constraint_id for item in snapshot.components] == ["clarity", "grounding"]


def test_hard_missing_and_conflict_are_separated() -> None:
    snapshot = calculate_energy(
        snapshot_id="energy:1",
        candidate_id="candidate:1",
        policy_ref="policy:1",
        energy_before=0,
        observations=(
            observation("hard", "safety", ObservationStatus.FAIL, 1000, hard=True),
            observation(
                "missing",
                "evidence",
                ObservationStatus.MISSING,
                500,
                required_missing=True,
            ),
            observation("conflict", "provenance", ObservationStatus.CONFLICT, 300),
        ),
    )
    assert snapshot.hard_failure_refs == ("hard",)
    assert snapshot.missing_evidence_refs == ("missing",)
    assert snapshot.conflict_refs == ("conflict",)


def test_conflicting_observation_id_fails_closed() -> None:
    with pytest.raises(ConflictingIdentifierError):
        calculate_energy(
            snapshot_id="energy:1",
            candidate_id="candidate:1",
            policy_ref="policy:1",
            energy_before=0,
            observations=(
                observation("same", "one", ObservationStatus.FAIL, 1),
                observation("same", "two", ObservationStatus.FAIL, 2),
            ),
        )
