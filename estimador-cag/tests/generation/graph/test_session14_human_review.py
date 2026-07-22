from __future__ import annotations

from copy import deepcopy

import pytest
from langgraph.types import Command

import app.generation.graph.nodes.session14_human_review as module
from app.generation.graph.nodes.session14_human_review import (
    IncompleteSession14AdjustmentError,
    StaleSession14HumanReviewError,
    build_session14_human_review_gate,
)
from app.generation.graph.review_state import (
    Session14EstimationGraphState,
)


def _component(
    component_id: str = "CMP-1",
) -> dict[str, object]:
    return {
        "component_id": component_id,
        "name": "Authentication",
        "hours": 40.0,
        "grounding_status": "low_confidence",
        "reference_budget_ids": ["BUD-1"],
        "reference_component_ids": ["REF-1"],
        "source_hours": [40.0],
        "source_range_low": 40.0,
        "source_range_high": 40.0,
        "dispersion": 0.0,
        "confidence": 0.5,
        "derivation_method": "median_recorded_hours",
        "review_reasons": ["Only one reference was available."],
    }


def _state(**overrides: object) -> Session14EstimationGraphState:
    component = _component()
    state = Session14EstimationGraphState(
        transcript="CLIENT-SECRET: build authentication.",
        estimation_id="estimate-14",
        thread_id="estimate:estimate-14",
        graph_version="session14.v1",
        component_estimates=[component],
        estimate={
            "components": [deepcopy(component)],
            "subtotal_hours": 40.0,
            "contingency_hours": 0.0,
            "total_hours": 40.0,
            "total_cost_eur": None,
            "currency": "EUR",
        },
        budget_matches=[{"budget_id": "BUD-1"}],
        status="needs_review",
        review_required=True,
        confidence=0.5,
        historical_range_status="within_range",
        human_review_revision=1,
        human_review_status="awaiting_human_review",
        human_review_reason_codes=["low_confidence"],
        human_review_actions=[],
        route_reason_code="human_review_required",
        current_agent="supervisor",
        next_agent="human_review_gate",
        errors=[],
        trace_events=[],
    )
    state.update(overrides)
    return state


def _decision(action: str, **overrides: object) -> dict[str, object]:
    decision: dict[str, object] = {
        "action": action,
        "expected_revision": 1,
        "actor": "reviewer@example.com",
        "idempotency_key": f"review-{action}-001",
    }
    decision.update(overrides)
    return decision


@pytest.mark.asyncio
async def test_gate_interrupts_with_sanitized_payload_and_approves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[dict[str, object]] = []

    def approve(payload: dict[str, object]) -> dict[str, object]:
        captured.append(deepcopy(payload))
        return _decision("approve")

    monkeypatch.setattr(module, "interrupt", approve)
    state = _state()
    before = deepcopy(state)

    command = await build_session14_human_review_gate()(state)

    assert isinstance(command, Command)
    assert command.goto == "finalize"
    assert state == before
    assert "CLIENT-SECRET" not in str(captured)
    assert captured[0]["reason_codes"] == ["low_confidence"]
    assert captured[0]["revision"] == 1

    update = command.update
    assert isinstance(update, dict)
    assert update["human_review_status"] == "approved"
    assert update["human_review_revision"] == 2
    assert update["status"] == "validated"
    assert update["review_required"] is False
    assert update["validation"] == {
        "is_coherent": False,
        "review_required": False,
        "status": "validated",
        "human_authorized": True,
    }
    assert update["human_review_actions"][0]["action"] == "approve"
    assert [event["event_type"] for event in update["trace_events"]] == [
        "session14_human_review_paused",
        "session14_human_review_approve",
    ]


@pytest.mark.asyncio
async def test_adjust_recalculates_and_revalidates_component_hours(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "interrupt",
        lambda payload: _decision(
            "adjust",
            reason="Use the reviewed discovery baseline.",
            adjustments=[
                {
                    "component_id": "CMP-1",
                    "hours": 52.0,
                    "evidence_refs": ["HUMAN-NOTE-7"],
                }
            ],
        ),
    )

    command = await build_session14_human_review_gate()(_state())
    update = command.update

    assert isinstance(update, dict)
    assert update["human_review_status"] == "adjusted"
    assert update["status"] == "validated"
    assert update["review_required"] is False
    assert update["confidence"] == 1.0
    assert update["estimate"]["subtotal_hours"] == 52.0
    assert update["estimate"]["total_hours"] == 52.0
    assert update["component_estimates"][0]["hours"] == 52.0
    assert (
        update["component_estimates"][0]["derivation_method"]
        == "human_adjustment"
    )
    assert update["human_review_actions"][0]["adjustments"] == [
        {
            "component_id": "CMP-1",
            "hours": 52.0,
            "evidence_refs": ["HUMAN-NOTE-7"],
        }
    ]


@pytest.mark.asyncio
async def test_adjust_fails_if_another_low_confidence_component_remains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    second = _component("CMP-2")
    state = _state(
        component_estimates=[_component(), second],
    )
    monkeypatch.setattr(
        module,
        "interrupt",
        lambda payload: _decision(
            "adjust",
            reason="Only one component was reviewed.",
            adjustments=[
                {
                    "component_id": "CMP-1",
                    "hours": 52.0,
                    "evidence_refs": ["HUMAN-NOTE-7"],
                }
            ],
        ),
    )

    with pytest.raises(
        IncompleteSession14AdjustmentError,
        match="review triggers active",
    ):
        await build_session14_human_review_gate()(state)


@pytest.mark.asyncio
async def test_reject_finishes_with_audited_needs_review_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "interrupt",
        lambda payload: _decision(
            "reject",
            reason="Historical support is insufficient.",
        ),
    )

    command = await build_session14_human_review_gate()(_state())
    update = command.update

    assert isinstance(update, dict)
    assert update["human_review_status"] == "rejected"
    assert update["status"] == "needs_review"
    assert update["review_required"] is True


@pytest.mark.asyncio
async def test_stale_revision_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "interrupt",
        lambda payload: _decision(
            "approve",
            expected_revision=1,
        ),
    )

    with pytest.raises(
        StaleSession14HumanReviewError,
        match="does not match",
    ):
        await build_session14_human_review_gate()(
            _state(human_review_revision=2)
        )
