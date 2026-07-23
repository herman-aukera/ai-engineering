from __future__ import annotations

from copy import deepcopy

import pytest

from app.generation.graph.nodes import final_estimate_review as module
from app.generation.graph.nodes.final_estimate_review import (
    StaleFinalEstimateReviewError,
    build_final_estimate_review_node,
)


def state(**overrides):
    value = {
        "human_review_mode": "required",
        "final_review_revision": 0,
        "review_required": False,
        "status": "validated",
        "estimate": {"total_hours": 40.0},
        "component_estimates": [
            {
                "component_id": "CMP-1",
                "name": "Authentication",
                "hours": 40.0,
                "grounding_status": "grounded",
                "reference_budget_ids": ["BUD-1"],
                "reference_component_ids": ["REF-1"],
                "source_hours": [40.0, 40.0],
                "source_range_low": 40.0,
                "source_range_high": 40.0,
                "dispersion": 0.0,
                "confidence": 1.0,
                "derivation_method": "median_recorded_hours",
                "review_reasons": [],
            }
        ],
        "critic_report": {"verdict": "accept", "issues": []},
        "boss_decision": {"action": "accept"},
    }
    value.update(overrides)
    return value


@pytest.mark.asyncio
async def test_risk_based_clean_estimate_skips_final_gate(monkeypatch) -> None:
    monkeypatch.setattr(module, "interrupt", lambda payload: pytest.fail(str(payload)))
    update = await build_final_estimate_review_node()(
        state(human_review_mode="risk_based")
    )
    assert update["final_review_status"] == "skipped"
    assert update["final_review_route"] == "complete"


@pytest.mark.asyncio
async def test_required_final_gate_records_approval(monkeypatch) -> None:
    monkeypatch.setattr(
        module,
        "interrupt",
        lambda payload: {
            "action": "approve",
            "expected_revision": payload["revision"],
            "actor": "reviewer@example.com",
        },
    )
    update = await build_final_estimate_review_node()(state())
    assert update["final_review_revision"] == 1
    assert update["final_review_status"] == "approved"
    assert update["final_review_record"]["actor"] == "reviewer@example.com"


@pytest.mark.asyncio
async def test_final_override_records_old_new_values_and_evidence(monkeypatch) -> None:
    monkeypatch.setattr(
        module,
        "interrupt",
        lambda payload: {
            "action": "override",
            "expected_revision": payload["revision"],
            "actor": "lead@example.com",
            "reason": "Approved discovery baseline.",
            "overrides": [
                {
                    "component_id": "CMP-1",
                    "hours": 52.0,
                    "evidence_refs": ["HUMAN-NOTE-7"],
                }
            ],
        },
    )
    original = state()
    snapshot = deepcopy(original)
    update = await build_final_estimate_review_node()(original)
    assert original == snapshot
    assert update["component_estimates"][0]["hours"] == 52.0
    assert update["component_estimates"][0]["derivation_method"] == "human_baseline_override"
    assert update["final_review_record"]["changes"] == [
        {
            "component_id": "CMP-1",
            "field": "hours",
            "old_value": 40.0,
            "new_value": 52.0,
            "evidence_refs": ["HUMAN-NOTE-7"],
        }
    ]


@pytest.mark.asyncio
async def test_stale_final_review_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(
        module,
        "interrupt",
        lambda payload: {
            "action": "approve",
            "expected_revision": payload["revision"] - 1,
            "actor": "reviewer@example.com",
        },
    )
    with pytest.raises(StaleFinalEstimateReviewError, match="does not match"):
        await build_final_estimate_review_node()(state(final_review_revision=4))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "route", "status"),
    [("reject", "stop", "rejected"), ("request_recovery", "recover", "recovery_requested")],
)
async def test_final_gate_routes_reject_and_recovery(monkeypatch, action, route, status) -> None:
    monkeypatch.setattr(
        module,
        "interrupt",
        lambda payload: {
            "action": action,
            "expected_revision": payload["revision"],
            "actor": "reviewer@example.com",
            "reason": "Evidence requires another decision.",
        },
    )
    update = await build_final_estimate_review_node()(state())
    assert update["final_review_route"] == route
    assert update["final_review_status"] == status
