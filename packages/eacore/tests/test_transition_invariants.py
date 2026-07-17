import pytest

from eacore.contracts import (
    DecisionEnvelope,
    EnergyComponent,
    EnergySnapshot,
    OutcomeClass,
    RepairRef,
    RepairResult,
    TransitionInvariantError,
)
from eacore.engine import verify_transition


def decision(outcome: OutcomeClass = OutcomeClass.ACCEPTED, authorization: str | None = "auth:1"):
    return DecisionEnvelope(
        decision_id="d",
        candidate_id="candidate:1",
        product_decision_code="accept",
        outcome_class=outcome,
        policy_ref="policy:1",
        energy_snapshot_ref="energy:1",
        authorization_ref=authorization,
        reason_summary="decision",
    )


def energy(*, delta: float = -1, hard=(), missing=(), conflicts=(), setup=False):
    before = 10.0
    after = before + delta
    return EnergySnapshot(
        energy_snapshot_id="energy:1",
        candidate_id="candidate:1",
        policy_ref="policy:1",
        energy_before=before,
        energy_after=after,
        energy_delta=delta,
        hard_failure_refs=hard,
        missing_evidence_refs=missing,
        conflict_refs=conflicts,
        components=(
            EnergyComponent(
                component_id="component:1",
                constraint_id="c",
                penalty=after,
                observation_refs=("o",),
            ),
        ),
        setup_work=setup,
        setup_work_justification="bounded schema bootstrap" if setup else None,
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"hard": ("hard",)},
        {"missing": ("missing",)},
        {"conflicts": ("conflict",)},
    ],
)
def test_accept_rejects_unresolved_blockers(kwargs) -> None:
    with pytest.raises(TransitionInvariantError):
        verify_transition(decision=decision(), energy=energy(**kwargs))


def test_accept_requires_improvement() -> None:
    with pytest.raises(TransitionInvariantError):
        verify_transition(decision=decision(), energy=energy(delta=0))


def test_bounded_setup_work_can_be_accepted() -> None:
    verify_transition(decision=decision(), energy=energy(delta=0, setup=True))


def test_accept_requires_independent_authorization() -> None:
    with pytest.raises(TransitionInvariantError):
        verify_transition(decision=decision(authorization=None), energy=energy())


def test_repeated_fingerprint_cannot_be_new_repair() -> None:
    repair = RepairRef(
        repair_id="r",
        source_candidate_id="old",
        target_candidate_id="candidate:1",
        repair_kind="rewrite",
        instruction_ref="instruction:1",
        result=RepairResult.NO_IMPROVEMENT,
        energy_before_ref="before",
        energy_after_ref="after",
    )
    with pytest.raises(TransitionInvariantError):
        verify_transition(
            decision=decision(OutcomeClass.CHANGE_REQUIRED),
            energy=energy(),
            previous_fingerprint="same",
            candidate_fingerprint="same",
            repair=repair,
        )


def test_non_improving_repair_cannot_be_marked_improved() -> None:
    repair = RepairRef(
        repair_id="r",
        source_candidate_id="old",
        target_candidate_id="candidate:1",
        repair_kind="rewrite",
        instruction_ref="instruction:1",
        result=RepairResult.IMPROVED,
        energy_before_ref="before",
        energy_after_ref="after",
    )
    with pytest.raises(TransitionInvariantError):
        verify_transition(
            decision=decision(OutcomeClass.CHANGE_REQUIRED),
            energy=energy(delta=0),
            repair=repair,
        )
