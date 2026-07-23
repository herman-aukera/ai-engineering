from __future__ import annotations

import pytest

from app.generation.graph.nodes import structure_review as structure_review_module
from app.generation.graph.nodes.structure_review import (
    StaleStructureReviewError,
    build_structure_review_node,
)
from app.generation.graph.review_state import ReviewedEstimationGraphState


def _state(**overrides) -> ReviewedEstimationGraphState:
    state: ReviewedEstimationGraphState = {
        "transcript": "Build a secure FastAPI onboarding platform.",
        "estimation_id": "11111111-1111-4111-8111-111111111111",
        "graph_version": "session13.v1",
        "requirements": [
            {"requirement_id": "req-1", "text": "Authenticate users with JWT."},
            {"requirement_id": "req-2", "text": "Persist accounts in PostgreSQL."},
        ],
        "components": [
            {
                "component_id": "cmp-auth",
                "name": "Authentication",
                "category": "backend",
                "requirement_ids": ["req-1", "req-2"],
            }
        ],
        "review_required": False,
        "errors": [],
        "trace_events": [],
        "human_review_mode": "risk_based",
        "structure_review_revision": 0,
    }
    state.update(overrides)
    return state


@pytest.mark.asyncio
async def test_disabled_mode_skips_structure_interrupt(monkeypatch) -> None:
    def fail_interrupt(payload):
        raise AssertionError(f"interrupt must not be called: {payload}")

    monkeypatch.setattr(structure_review_module, "interrupt", fail_interrupt)
    node = build_structure_review_node()

    update = await node(_state(human_review_mode="disabled"))

    assert update["structure_review_status"] == "skipped"
    assert update["structure_route"] == "continue"
    assert update["trace_events"][0]["event_type"] == "structure_review_skipped"


@pytest.mark.asyncio
async def test_clean_risk_based_structure_skips_interrupt(monkeypatch) -> None:
    def fail_interrupt(payload):
        raise AssertionError(f"interrupt must not be called: {payload}")

    monkeypatch.setattr(structure_review_module, "interrupt", fail_interrupt)
    node = build_structure_review_node()

    update = await node(_state())

    assert update["structure_review_status"] == "skipped"
    assert update["structure_route"] == "continue"


@pytest.mark.asyncio
async def test_required_mode_interrupts_with_checkpoint_safe_payload(monkeypatch) -> None:
    captured = {}

    def fake_interrupt(payload):
        captured.update(payload)
        return {
            "action": "approve",
            "expected_revision": 0,
        }

    monkeypatch.setattr(structure_review_module, "interrupt", fake_interrupt)
    node = build_structure_review_node()

    update = await node(_state(human_review_mode="required"))

    assert captured["gate"] == "structure_review"
    assert captured["revision"] == 0
    assert captured["requirements"][0]["requirement_id"] == "req-1"
    assert captured["components"][0]["component_id"] == "cmp-auth"
    assert captured["allowed_actions"] == ["approve", "edit", "reject", "regenerate"]
    assert update["structure_review_revision"] == 1
    assert update["structure_review_status"] == "approved"
    assert update["structure_route"] == "continue"
    assert update["review_required"] is False


@pytest.mark.asyncio
async def test_human_can_edit_structure_before_estimation(monkeypatch) -> None:
    def fake_interrupt(payload):
        return {
            "action": "edit",
            "expected_revision": payload["revision"],
            "requirements": [
                {"requirement_id": "req-1", "text": "Use OAuth2 and JWT."},
                {"requirement_id": "req-3", "text": "Add an audit trail."},
            ],
            "components": [
                {
                    "component_id": "cmp-identity",
                    "name": "Identity and audit",
                    "category": "backend",
                    "requirement_ids": ["req-1", "req-3"],
                }
            ],
        }

    monkeypatch.setattr(structure_review_module, "interrupt", fake_interrupt)
    node = build_structure_review_node()

    update = await node(_state(human_review_mode="required"))

    assert update["requirements"] == [
        {"requirement_id": "req-1", "text": "Use OAuth2 and JWT."},
        {"requirement_id": "req-3", "text": "Add an audit trail."},
    ]
    assert update["components"][0]["component_id"] == "cmp-identity"
    assert update["structure_review_status"] == "edited"
    assert update["structure_route"] == "continue"
    assert update["trace_events"][0]["event_type"] == "structure_edited"


@pytest.mark.asyncio
async def test_stale_human_response_is_rejected(monkeypatch) -> None:
    def fake_interrupt(payload):
        return {
            "action": "approve",
            "expected_revision": payload["revision"] - 1,
        }

    monkeypatch.setattr(structure_review_module, "interrupt", fake_interrupt)
    node = build_structure_review_node()

    with pytest.raises(StaleStructureReviewError, match="does not match"):
        await node(
            _state(
                human_review_mode="required",
                structure_review_revision=3,
            )
        )


@pytest.mark.asyncio
async def test_reject_stops_before_estimation(monkeypatch) -> None:
    def fake_interrupt(payload):
        return {
            "action": "reject",
            "expected_revision": payload["revision"],
            "reason": "The structure omits the client approval workflow.",
        }

    monkeypatch.setattr(structure_review_module, "interrupt", fake_interrupt)
    node = build_structure_review_node()

    update = await node(_state(human_review_mode="required"))

    assert update["status"] == "needs_review"
    assert update["review_required"] is True
    assert update["structure_review_status"] == "rejected"
    assert update["structure_route"] == "stop"
    assert update["structure_review_record"]["reason"] == (
        "The structure omits the client approval workflow."
    )


@pytest.mark.asyncio
async def test_regenerate_routes_back_to_structure_generation(monkeypatch) -> None:
    def fake_interrupt(payload):
        return {
            "action": "regenerate",
            "expected_revision": payload["revision"],
            "reason": "Split identity and audit into separate components.",
        }

    monkeypatch.setattr(structure_review_module, "interrupt", fake_interrupt)
    node = build_structure_review_node()

    update = await node(_state(human_review_mode="required"))

    assert update["structure_review_status"] == "regeneration_requested"
    assert update["structure_route"] == "regenerate"
    assert update["review_required"] is True
