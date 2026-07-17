from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.schemas.v3_energy import ConstraintObservation, EstimateDecisionLedgerEntry
from app.services.v3_estimation_energy import (
    append_ledger_entries,
    build_estimate_energy_card,
    calculate_constraint_energy,
    candidate_fingerprint,
    classify_repair,
)


def test_candidate_fingerprint_is_stable_for_key_order() -> None:
    left = candidate_fingerprint({"b": 2, "a": 1})
    right = candidate_fingerprint({"a": 1, "b": 2})
    assert left == right


def test_hard_failures_dominate_soft_energy() -> None:
    snapshot = calculate_constraint_energy(
        candidate_id="candidate-1",
        policy_version="estimate-policy-1",
        energy_before=200,
        observations=[
            ConstraintObservation(
                observation_id="obs-arithmetic",
                code="arithmetic_mismatch",
                status="fail",
                penalty=1,
                hard_blocking=True,
                summary="Task and module totals do not reconcile.",
            ),
            ConstraintObservation(
                observation_id="obs-confidence",
                code="low_confidence",
                status="fail",
                penalty=40,
                summary="Confidence is below the policy threshold.",
            ),
        ],
    )

    assert snapshot.energy_after == 10_040
    assert snapshot.hard_violations == ["arithmetic_mismatch"]
    assert snapshot.soft_penalties == {"low_confidence": 40}


def test_missing_evidence_cannot_be_treated_as_pass() -> None:
    snapshot = calculate_constraint_energy(
        candidate_id="candidate-1",
        policy_version="estimate-policy-1",
        energy_before=0,
        observations=[
            ConstraintObservation(
                observation_id="obs-provenance",
                code="missing_provenance",
                status="missing",
                hard_blocking=True,
                summary="Required provenance is absent.",
            )
        ],
    )
    card = build_estimate_energy_card(snapshot=snapshot, disposition="human_review", repairs=0)
    assert snapshot.missing_evidence == ["missing_provenance"]
    assert card.hard_constraints_passed is False


def test_repair_requires_lower_energy_and_no_hard_gap() -> None:
    before = calculate_constraint_energy(
        candidate_id="candidate-1",
        policy_version="estimate-policy-1",
        energy_before=200,
        observations=[
            ConstraintObservation(
                observation_id="obs-confidence-1",
                code="low_confidence",
                status="fail",
                penalty=100,
                summary="Confidence is low.",
            )
        ],
    )
    blocked_after = calculate_constraint_energy(
        candidate_id="candidate-2",
        policy_version="estimate-policy-1",
        energy_before=before.energy_after,
        observations=[
            ConstraintObservation(
                observation_id="obs-provenance-2",
                code="missing_provenance",
                status="missing",
                hard_blocking=True,
                summary="Evidence is still missing.",
            )
        ],
    )
    improved_after = calculate_constraint_energy(
        candidate_id="candidate-3",
        policy_version="estimate-policy-1",
        energy_before=before.energy_after,
        observations=[
            ConstraintObservation(
                observation_id="obs-confidence-3",
                code="confidence_ok",
                status="pass",
                summary="Confidence meets the policy threshold.",
            )
        ],
    )

    assert classify_repair(before, blocked_after) == "no_improvement"
    assert classify_repair(before, improved_after) == "improved"
    assert improved_after.energy_delta < 0


def test_decision_ledger_is_idempotent_and_conflicting_reuse_fails() -> None:
    entry = EstimateDecisionLedgerEntry(
        decision_id="decision-1",
        estimation_id="estimate-1",
        thread_id="estimate:estimate-1",
        checkpoint_id="checkpoint-1",
        candidate_id="candidate-1",
        critic_report_ref="critic-1",
        energy_snapshot_id="energy-1",
        boss_action="accept",
        policy_version="estimate-policy-1",
        reason="All hard constraints pass.",
        recorded_at=datetime(2026, 7, 17, tzinfo=UTC),
    )
    assert append_ledger_entries([entry], [entry]) == [entry]

    conflicting = entry.model_copy(update={"boss_action": "reject"})
    with pytest.raises(ValueError, match="conflicting decision ID"):
        append_ledger_entries([entry], [conflicting])


def test_conflicting_observation_replay_fails_closed() -> None:
    first = ConstraintObservation(
        observation_id="obs-1",
        code="confidence",
        status="pass",
        summary="Confidence passes.",
    )
    conflicting = first.model_copy(update={"status": "fail", "penalty": 10})
    with pytest.raises(ValueError, match="conflicting observation ID"):
        calculate_constraint_energy(
            candidate_id="candidate-1",
            policy_version="estimate-policy-1",
            energy_before=0,
            observations=[first, conflicting],
        )
