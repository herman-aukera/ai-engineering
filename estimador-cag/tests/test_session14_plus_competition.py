from __future__ import annotations

import pytest

from app.generation.graph.nodes.session14_plus_competition import (
    build_session14_plus_competition_node,
)
from app.generation.graph.session14_plus_state import (
    new_session14_plus_estimation_graph_state,
)
from app.services.session14_plus_competition import (
    EstimateCompetitionPolicy,
    build_estimate_competition,
)


def _estimate(
    *,
    component_id: str = "CMP-1",
    hours: float | None = 42.0,
    low: float | None = 38.0,
    high: float | None = 46.0,
    confidence: float = 0.85,
) -> dict[str, object]:
    return {
        "component_id": component_id,
        "name": f"Component {component_id}",
        "hours": hours,
        "grounding_status": "grounded",
        "reference_budget_ids": [f"BUD-{component_id}"],
        "reference_component_ids": [f"REF-{component_id}"],
        "source_hours": [40.0, 44.0],
        "source_range_low": low,
        "source_range_high": high,
        "dispersion": 4.0,
        "confidence": confidence,
        "derivation_method": "median_historical_hours",
        "review_reasons": [],
    }


def test_bounded_competition_is_deterministic_and_accepts_synthesis() -> None:
    first = build_estimate_competition(
        [_estimate()],
        estimation_id="EST-COMP-1",
    )
    second = build_estimate_competition(
        [_estimate()],
        estimation_id="EST-COMP-1",
    )

    assert first == second
    assert [candidate.variant for candidate in first.candidates] == [
        "baseline",
        "aggressive",
        "conservative",
        "synthesized",
    ]
    assert first.assessment.disposition == "accept_synthesized"
    assert first.assessment.review_required is False
    assert first.assessment.energy_snapshot.conflicts == []
    assert first.assessment.selected_candidate_id == (
        first.assessment.synthesized_candidate_id
    )
    assert first.selected_component_estimates[0]["derivation_method"] == (
        "session14_plus_competition_synthesis"
    )


def test_material_candidate_divergence_fails_closed_to_human_review() -> None:
    outcome = build_estimate_competition(
        [_estimate(hours=40.0, low=20.0, high=80.0)],
        estimation_id="EST-COMP-2",
    )

    assert outcome.assessment.divergence_ratio == 1.1
    assert outcome.assessment.disposition == "human_review"
    assert outcome.assessment.review_required is True
    assert outcome.assessment.selected_candidate_id == (
        outcome.assessment.baseline_candidate_id
    )
    assert "competition_material_divergence" in (
        outcome.assessment.energy_snapshot.conflicts
    )
    assert "material_candidate_divergence" in (
        outcome.selected_component_estimates[0]["review_reasons"]
    )


def test_missing_component_hours_are_hard_missing_evidence() -> None:
    outcome = build_estimate_competition(
        [_estimate(hours=None, low=None, high=None)],
        estimation_id="EST-COMP-3",
    )

    assert outcome.assessment.review_required is True
    assert "competition_component_hours_complete" in (
        outcome.assessment.energy_snapshot.missing_evidence
    )
    assert all(candidate.total_hours is None for candidate in outcome.candidates)


@pytest.mark.asyncio
async def test_competition_node_returns_partial_update_and_routes_to_supervisor() -> None:
    state = new_session14_plus_estimation_graph_state(
        transcript="Build a component.",
        estimation_id="EST-COMP-4",
    )
    state["component_estimates"] = [_estimate()]
    node = build_session14_plus_competition_node(
        policy=EstimateCompetitionPolicy(
            material_divergence_threshold=0.30
        )
    )

    command = await node(state)

    assert command.goto == "supervisor"
    assert command.update["plus_competition_completed"] is True
    assert len(command.update["plus_competition_candidates"]) == 4
    assert command.update["plus_competition_assessment"]["disposition"] == (
        "accept_synthesized"
    )
    assert command.update["review_required"] is False
    assert command.update["trace_events"][0]["node"] == (
        "candidate_competition"
    )
