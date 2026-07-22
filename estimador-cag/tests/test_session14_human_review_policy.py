from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.generation.graph.review_state import (
    merge_session14_human_review_actions,
)
from app.schemas.session14_human_review import (
    Session14HumanReviewDecision,
)
from app.services.session14_human_review import (
    action_record_from_decision,
    action_record_matches_decision,
    assess_session14_human_review,
    build_session14_interrupt_payload,
)


def _state(**overrides: object) -> dict[str, object]:
    state: dict[str, object] = {
        "estimation_id": "estimate-14",
        "thread_id": "estimate:estimate-14",
        "transcript": "CLIENT-SECRET: build authentication.",
        "review_required": False,
        "route_reason_code": "human_review_required",
        "estimate": {"total_hours": 40.0},
        "budget_matches": [{"budget_id": "BUD-1"}],
        "component_estimates": [
            {
                "component_id": "CMP-1",
                "hours": 40.0,
                "grounding_status": "grounded",
                "reference_budget_ids": ["BUD-1", "BUD-2"],
                "source_hours": [32.0, 40.0, 48.0],
                "source_range_low": 32.0,
                "source_range_high": 48.0,
                "confidence": 0.8,
                "derivation_method": "median_recorded_hours",
            }
        ],
        "errors": [],
    }
    state.update(overrides)
    return state


def test_policy_requires_review_below_configured_confidence() -> None:
    state = _state()
    state["component_estimates"][0]["confidence"] = 0.64

    assessment = assess_session14_human_review(
        state,
        confidence_threshold=0.65,
    )

    assert assessment.required is True
    assert assessment.reason_codes == ("low_confidence",)
    assert assessment.confidence == 0.64
    assert assessment.historical_range_status == "within_range"


def test_policy_detects_outside_range_and_no_precedent() -> None:
    outside = _state()
    outside["component_estimates"][0]["hours"] = 52.0
    outside_assessment = assess_session14_human_review(outside)

    no_precedent = _state(
        component_estimates=[
            {
                "component_id": "CMP-1",
                "hours": None,
                "grounding_status": "no_data",
                "reference_budget_ids": [],
                "source_hours": [],
                "source_range_low": None,
                "source_range_high": None,
                "confidence": 0.0,
                "derivation_method": "no_recorded_hours",
            }
        ],
        budget_matches=[],
    )
    no_precedent_assessment = assess_session14_human_review(
        no_precedent
    )

    assert outside_assessment.reason_codes == (
        "outside_historical_range",
    )
    assert outside_assessment.historical_range_status == "outside_range"
    assert no_precedent_assessment.reason_codes == (
        "low_confidence",
        "no_precedent",
    )
    assert no_precedent_assessment.historical_range_status == "unavailable"


def test_interrupt_payload_is_allow_listed_and_sanitized() -> None:
    state = _state()
    state["component_estimates"][0]["confidence"] = 0.5
    state["errors"] = [
        {
            "code": "low_confidence_component_estimate",
            "message": "CLIENT-SECRET must never be exposed.",
        }
    ]
    assessment = assess_session14_human_review(state)

    payload = build_session14_interrupt_payload(
        state,
        assessment=assessment,
        revision=1,
    )

    assert set(payload) == {
        "gate",
        "estimation_id",
        "thread_id",
        "revision",
        "reason_codes",
        "estimate_summary",
        "confidence",
        "historical_range_status",
        "evidence_count",
        "active_findings",
        "allowed_actions",
    }
    assert payload["allowed_actions"] == ["approve", "adjust", "reject"]
    assert payload["active_findings"] == [
        "low_confidence_component_estimate"
    ]
    assert "CLIENT-SECRET" not in str(payload)
    assert "transcript" not in str(payload)


def test_decision_contract_and_action_record_are_replay_safe() -> None:
    decision = Session14HumanReviewDecision(
        action="adjust",
        expected_revision=1,
        actor="reviewer@example.com",
        reason="Use the signed discovery baseline.",
        idempotency_key="review-action-001",
        adjustments=[
            {
                "component_id": "CMP-1",
                "hours": 52.0,
                "evidence_refs": ["HUMAN-NOTE-7"],
            }
        ],
    )
    record = action_record_from_decision(
        estimation_id="estimate-14",
        decision=decision,
    )

    assert action_record_matches_decision(record, decision) is True
    assert merge_session14_human_review_actions(
        [deepcopy(record)],
        [deepcopy(record)],
    ) == [record]

    conflicting = deepcopy(record)
    conflicting["actor"] = "attacker@example.com"
    with pytest.raises(ValueError, match="conflicting idempotency_key"):
        merge_session14_human_review_actions([record], [conflicting])


@pytest.mark.parametrize(
    "payload",
    [
        {
            "action": "adjust",
            "expected_revision": 1,
            "actor": "reviewer",
            "reason": "Missing typed adjustment.",
            "idempotency_key": "review-action-002",
        },
        {
            "action": "reject",
            "expected_revision": 1,
            "actor": "reviewer",
            "idempotency_key": "review-action-003",
        },
        {
            "action": "approve",
            "expected_revision": 1,
            "actor": "reviewer",
            "idempotency_key": "bad key with spaces",
        },
    ],
)
def test_decision_contract_rejects_incomplete_or_unsafe_values(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        Session14HumanReviewDecision.model_validate(payload)
