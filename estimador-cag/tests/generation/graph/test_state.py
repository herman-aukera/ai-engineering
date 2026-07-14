from __future__ import annotations

import json
import operator
from typing import Annotated, get_args, get_origin, get_type_hints

import pytest

from app.generation.graph.state import (
    EstimationGraphState,
    new_estimation_graph_state,
)

ACCUMULATOR_FIELDS = (
    "budget_matches",
    "errors",
    "trace_events",
)


def _reducer_metadata(field_name: str) -> tuple[object, ...]:
    hints = get_type_hints(EstimationGraphState, include_extras=True)
    annotation = hints[field_name]

    assert get_origin(annotation) is Annotated
    return get_args(annotation)[1:]


@pytest.mark.parametrize("field_name", ACCUMULATOR_FIELDS)
def test_accumulator_fields_use_operator_add(field_name: str) -> None:
    assert operator.add in _reducer_metadata(field_name)


def test_initial_state_has_checkpoint_safe_defaults() -> None:
    state = new_estimation_graph_state(
        transcript="The client needs authentication and audit logging.",
        estimation_id="estimate-123",
    )

    assert state["estimation_id"] == "estimate-123"
    assert state["graph_version"] == "session13.v1"
    assert state["status"] == "pending"
    assert state["review_required"] is False

    assert state["requirements"] == []
    assert state["components"] == []
    assert state["budget_matches"] == []
    assert state["component_estimates"] == []
    assert state["errors"] == []
    assert state["trace_events"] == []
    assert state["provider_metadata"] == {}
    assert state["execution_metadata"] == {}

    serialized = json.dumps(state, sort_keys=True)
    assert '"estimation_id": "estimate-123"' in serialized


def test_initial_state_does_not_share_mutable_accumulators() -> None:
    first = new_estimation_graph_state(
        transcript="First valid transcript.",
        estimation_id="estimate-first",
    )
    second = new_estimation_graph_state(
        transcript="Second valid transcript.",
        estimation_id="estimate-second",
    )

    first["errors"].append(
        {
            "code": "example",
            "message": "Example issue.",
            "node": "extract_requirements",
            "severity": "warning",
        }
    )

    assert second["errors"] == []


def test_operator_add_appends_only_new_reducer_items() -> None:
    existing = [
        {
            "code": "existing",
            "message": "Existing issue.",
            "node": "search_budgets",
            "severity": "warning",
        }
    ]
    delta = [
        {
            "code": "new",
            "message": "New issue.",
            "node": "generate_estimate",
            "severity": "error",
        }
    ]

    merged = operator.add(existing, delta)

    assert merged == [existing[0], delta[0]]
    assert existing == [existing[0]]
    assert delta == [delta[0]]


@pytest.mark.parametrize(
    ("transcript", "estimation_id", "expected_message"),
    [
        ("", "estimate-1", "transcript must not be blank"),
        ("   ", "estimate-1", "transcript must not be blank"),
        ("Valid transcript.", "", "estimation_id must not be blank"),
        ("Valid transcript.", "   ", "estimation_id must not be blank"),
    ],
)
def test_initial_state_rejects_blank_identifiers(
    transcript: str,
    estimation_id: str,
    expected_message: str,
) -> None:
    with pytest.raises(ValueError, match=expected_message):
        new_estimation_graph_state(
            transcript=transcript,
            estimation_id=estimation_id,
        )
