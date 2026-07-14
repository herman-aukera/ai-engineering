from __future__ import annotations

from copy import deepcopy

import pytest

from app.generation.graph.nodes.validate_and_consolidate import (
    build_validate_and_consolidate_node,
)
from app.generation.graph.state import new_estimation_graph_state

GROUNDED_AUTH = {
    "component_id": "CMP-001",
    "name": "JWT authentication",
    "hours": 40.0,
    "grounding_status": "grounded",
    "reference_budget_ids": [
        "BUD-101",
        "BUD-102",
        "BUD-103",
    ],
    "reference_component_ids": [
        "AUTH-01",
        "AUTH-02",
        "AUTH-03",
    ],
    "source_hours": [32.0, 40.0, 48.0],
    "source_range_low": 32.0,
    "source_range_high": 48.0,
    "dispersion": 0.4,
    "confidence": 0.8,
    "derivation_method": "median_recorded_hours",
    "review_reasons": [],
}

GROUNDED_AUDIT = {
    "component_id": "CMP-002",
    "name": "Audit logging",
    "hours": 24.0,
    "grounding_status": "grounded",
    "reference_budget_ids": [
        "BUD-201",
        "BUD-202",
        "BUD-203",
    ],
    "reference_component_ids": [
        "AUDIT-01",
        "AUDIT-02",
        "AUDIT-03",
    ],
    "source_hours": [20.0, 24.0, 28.0],
    "source_range_low": 20.0,
    "source_range_high": 28.0,
    "dispersion": 0.3333,
    "confidence": 0.83,
    "derivation_method": "median_recorded_hours",
    "review_reasons": [],
}


def _state(
    estimates: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    state = new_estimation_graph_state(
        transcript="JWT authentication and audit logging are required.",
        estimation_id="estimate-123",
    )
    state["component_estimates"] = deepcopy(
        [GROUNDED_AUTH, GROUNDED_AUDIT]
        if estimates is None
        else estimates
    )
    return state


@pytest.mark.asyncio
async def test_clean_estimate_is_validated_without_mutating_input() -> None:
    node = build_validate_and_consolidate_node()
    state = _state()
    original_state = deepcopy(state)

    update = await node(state)

    assert state == original_state
    assert set(update) == {
        "estimate",
        "status",
        "review_required",
        "trace_events",
    }

    assert update["estimate"] == {
        "components": [
            GROUNDED_AUTH,
            GROUNDED_AUDIT,
        ],
        "subtotal_hours": 64.0,
        "contingency_hours": 0.0,
        "total_hours": 64.0,
        "total_cost_eur": None,
        "currency": "EUR",
    }
    assert update["status"] == "validated"
    assert update["review_required"] is False

    assert update["trace_events"] == [
        {
            "event_type": "estimate_validated",
            "node": "validate_and_consolidate",
            "summary": (
                "Validated 2 grounded component estimates "
                "totaling 64.0 hours."
            ),
            "evidence_refs": [
                "CMP-001",
                "CMP-002",
                "BUD-101",
                "BUD-102",
                "BUD-103",
                "BUD-201",
                "BUD-202",
                "BUD-203",
            ],
            "state_delta_keys": [
                "estimate",
                "status",
                "review_required",
                "trace_events",
            ],
        }
    ]


@pytest.mark.asyncio
async def test_low_confidence_component_sets_needs_review() -> None:
    low_confidence = deepcopy(GROUNDED_AUDIT)
    low_confidence["grounding_status"] = "low_confidence"
    low_confidence["source_hours"] = [24.0]
    low_confidence["source_range_low"] = 24.0
    low_confidence["source_range_high"] = 24.0
    low_confidence["dispersion"] = 0.0
    low_confidence["confidence"] = 0.5
    low_confidence["reference_budget_ids"] = ["BUD-201"]
    low_confidence["reference_component_ids"] = ["AUDIT-01"]
    low_confidence["review_reasons"] = [
        "Only one recorded-hours reference was available."
    ]

    node = build_validate_and_consolidate_node()
    update = await node(
        _state([GROUNDED_AUTH, low_confidence])
    )

    assert update["status"] == "needs_review"
    assert update["review_required"] is True
    assert update["estimate"]["subtotal_hours"] == 64.0
    assert update["estimate"]["total_hours"] == 64.0
    assert "errors" not in update

    assert update["trace_events"][0]["event_type"] == (
        "estimate_needs_review"
    )
    assert update["trace_events"][0]["summary"] == (
        "Consolidated 2 component estimates; "
        "1 requires review."
    )


@pytest.mark.asyncio
async def test_no_data_keeps_partial_subtotal_but_no_total() -> None:
    no_data = deepcopy(GROUNDED_AUDIT)
    no_data["hours"] = None
    no_data["grounding_status"] = "no_data"
    no_data["source_hours"] = []
    no_data["source_range_low"] = None
    no_data["source_range_high"] = None
    no_data["dispersion"] = None
    no_data["confidence"] = 0.0
    no_data["derivation_method"] = "no_recorded_hours"
    no_data["review_reasons"] = [
        "No recorded hours were available."
    ]

    node = build_validate_and_consolidate_node()
    update = await node(
        _state([GROUNDED_AUTH, no_data])
    )

    estimate = update["estimate"]

    assert estimate["subtotal_hours"] == 40.0
    assert estimate["contingency_hours"] is None
    assert estimate["total_hours"] is None
    assert estimate["total_cost_eur"] is None
    assert update["status"] == "needs_review"
    assert update["review_required"] is True


@pytest.mark.asyncio
async def test_conflicting_component_sets_needs_review() -> None:
    conflict = deepcopy(GROUNDED_AUTH)
    conflict["hours"] = 25.0
    conflict["grounding_status"] = "conflict"
    conflict["source_hours"] = [10.0, 40.0]
    conflict["source_range_low"] = 10.0
    conflict["source_range_high"] = 40.0
    conflict["dispersion"] = 1.2
    conflict["confidence"] = 0.25
    conflict["reference_budget_ids"] = [
        "BUD-101",
        "BUD-102",
    ]
    conflict["reference_component_ids"] = [
        "AUTH-01",
        "AUTH-02",
    ]
    conflict["review_reasons"] = [
        (
            "Reference-hour dispersion is at or above "
            "the conflict threshold."
        )
    ]

    node = build_validate_and_consolidate_node()
    update = await node(
        _state([conflict, GROUNDED_AUDIT])
    )

    assert update["status"] == "needs_review"
    assert update["review_required"] is True
    assert update["estimate"]["total_hours"] == 49.0


@pytest.mark.asyncio
async def test_existing_issue_forces_review_without_readding_it() -> None:
    node = build_validate_and_consolidate_node()
    state = _state()
    state["errors"] = [
        {
            "code": "upstream_warning",
            "message": "An upstream invariant requires review.",
            "node": "search_budgets",
            "severity": "warning",
        }
    ]

    update = await node(state)

    assert update["status"] == "needs_review"
    assert update["review_required"] is True
    assert "errors" not in update
    assert state["errors"] == [
        {
            "code": "upstream_warning",
            "message": "An upstream invariant requires review.",
            "node": "search_budgets",
            "severity": "warning",
        }
    ]


@pytest.mark.asyncio
async def test_existing_review_flag_cannot_be_cleared() -> None:
    node = build_validate_and_consolidate_node()
    state = _state()
    state["review_required"] = True

    update = await node(state)

    assert update["status"] == "needs_review"
    assert update["review_required"] is True


@pytest.mark.asyncio
async def test_mismatched_existing_total_is_recomputed_and_flagged() -> None:
    node = build_validate_and_consolidate_node()
    state = _state()
    state["estimate"] = {
        "components": deepcopy(
            [GROUNDED_AUTH, GROUNDED_AUDIT]
        ),
        "subtotal_hours": 64.0,
        "contingency_hours": 0.0,
        "total_hours": 999.0,
        "total_cost_eur": None,
        "currency": "EUR",
    }

    update = await node(state)

    assert update["estimate"]["total_hours"] == 64.0
    assert update["status"] == "needs_review"
    assert update["review_required"] is True
    assert update["errors"] == [
        {
            "code": "estimate_total_mismatch",
            "message": (
                "A pre-existing aggregate estimate did not match "
                "the component-derived arithmetic."
            ),
            "node": "validate_and_consolidate",
            "severity": "error",
        }
    ]


@pytest.mark.asyncio
async def test_matching_existing_estimate_is_idempotent() -> None:
    node = build_validate_and_consolidate_node()
    state = _state()
    state["estimate"] = {
        "components": deepcopy(
            [GROUNDED_AUTH, GROUNDED_AUDIT]
        ),
        "subtotal_hours": 64.0,
        "contingency_hours": 0.0,
        "total_hours": 64.0,
        "total_cost_eur": None,
        "currency": "EUR",
    }

    update = await node(state)

    assert update["status"] == "validated"
    assert update["review_required"] is False
    assert "errors" not in update


@pytest.mark.asyncio
async def test_missing_component_estimates_fails_closed() -> None:
    node = build_validate_and_consolidate_node()
    state = new_estimation_graph_state(
        transcript="Valid transcript.",
        estimation_id="estimate-missing",
    )

    update = await node(state)

    assert update["status"] == "needs_review"
    assert update["review_required"] is True
    assert update["estimate"] == {
        "components": [],
        "subtotal_hours": None,
        "contingency_hours": None,
        "total_hours": None,
        "total_cost_eur": None,
        "currency": "EUR",
    }
    assert update["errors"][0]["code"] == (
        "missing_component_estimates"
    )
    assert update["trace_events"][0]["event_type"] == (
        "estimate_validation_failed"
    )


@pytest.mark.asyncio
async def test_duplicate_component_estimates_fail_closed() -> None:
    node = build_validate_and_consolidate_node()

    update = await node(
        _state(
            [
                GROUNDED_AUTH,
                deepcopy(GROUNDED_AUTH),
            ]
        )
    )

    assert update["status"] == "needs_review"
    assert update["review_required"] is True
    assert update["errors"][0]["code"] == (
        "invalid_component_estimates"
    )


@pytest.mark.asyncio
async def test_component_hours_must_equal_source_median() -> None:
    invalid = deepcopy(GROUNDED_AUTH)
    invalid["hours"] = 999.0

    node = build_validate_and_consolidate_node()
    update = await node(_state([invalid]))

    assert update["status"] == "needs_review"
    assert update["errors"][0]["code"] == (
        "invalid_component_estimates"
    )
