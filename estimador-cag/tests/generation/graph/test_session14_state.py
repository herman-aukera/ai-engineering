from __future__ import annotations

from typing import Annotated, get_args, get_origin, get_type_hints

import pytest

from app.generation.graph import review_state
from app.generation.graph.review_state import (
    AgentContribution,
    Session14EstimationGraphState,
    merge_agent_contributions,
)


def _contribution(
    *,
    contribution_id: str = "contribution-1",
    sequence: int = 1,
    summary: str = "Extracted atomic requirements.",
) -> AgentContribution:
    return AgentContribution(
        contribution_id=contribution_id,
        agent_id="requirements_extractor",
        sequence=sequence,
        summary=summary,
        state_delta_keys=["requirements"],
    )


def test_session14_state_extends_plus_state_and_registers_reducer() -> None:
    hints = get_type_hints(
        Session14EstimationGraphState,
        include_extras=True,
    )

    assert {
        "transcript",
        "boss_decision",
        "requirements_extraction_completed",
        "budget_search_completed",
        "validation",
        "confidence",
        "routing_steps",
        "max_routing_steps",
        "current_agent",
        "previous_agent",
        "next_agent",
        "route_reason_code",
        "agent_contributions",
    } <= hints.keys()

    contribution_annotation = hints["agent_contributions"]

    assert get_origin(contribution_annotation) is Annotated
    assert merge_agent_contributions in get_args(contribution_annotation)[1:]


def test_identical_contribution_replay_is_idempotent() -> None:
    contribution = _contribution()
    current = [contribution]

    merged = merge_agent_contributions(
        current,
        [dict(contribution)],
    )

    assert merged == [contribution]
    assert current == [contribution]


def test_contributions_have_deterministic_sequence_and_id_order() -> None:
    merged = merge_agent_contributions(
        [],
        [
            _contribution(contribution_id="contribution-c", sequence=2),
            _contribution(contribution_id="contribution-b", sequence=1),
            _contribution(contribution_id="contribution-a", sequence=1),
        ],
    )

    assert [item["contribution_id"] for item in merged] == [
        "contribution-a",
        "contribution-b",
        "contribution-c",
    ]


def test_conflicting_contribution_id_fails_closed_without_mutation() -> None:
    original = _contribution(summary="Original contribution.")
    current = [original]

    with pytest.raises(ValueError, match="contribution-1"):
        merge_agent_contributions(
            current,
            [_contribution(summary="Conflicting contribution.")],
        )

    assert current == [original]


def test_blank_contribution_id_fails_closed() -> None:
    with pytest.raises(ValueError, match="contribution_id"):
        merge_agent_contributions(
            [],
            [_contribution(contribution_id=" ")],
        )
def _route_event(
    *,
    route_event_id: str = "estimate-14:supervisor-route:1",
    sequence: int = 1,
    next_agent: str = "requirements_extractor",
    reason: str = "Requirements extraction has not completed.",
) -> dict[str, object]:
    return {
        "route_event_id": route_event_id,
        "sequence": sequence,
        "next_agent": next_agent,
        "reason_code": "missing_requirements",
        "reason": reason,
    }


def _route_event_reducer():
    reducer = getattr(
        review_state,
        "merge_supervisor_route_events",
        None,
    )
    assert callable(reducer)
    return reducer


def test_session14_state_registers_replay_safe_route_event_reducer() -> None:
    hints = get_type_hints(
        Session14EstimationGraphState,
        include_extras=True,
    )

    assert "route_events" in hints

    annotation = hints["route_events"]
    reducer = getattr(
        review_state,
        "merge_supervisor_route_events",
        None,
    )

    assert get_origin(annotation) is Annotated
    assert callable(reducer)
    assert reducer in get_args(annotation)[1:]


def test_identical_route_event_replay_is_idempotent_and_ordered() -> None:
    reducer = _route_event_reducer()
    later = _route_event(
        route_event_id="estimate-14:supervisor-route:2",
        sequence=2,
        next_agent="budget_searcher",
        reason="Budget search has not completed.",
    )
    earlier = _route_event()

    current = [later]

    merged = reducer(
        current,
        [
            dict(later),
            earlier,
        ],
    )

    assert [
        event["route_event_id"]
        for event in merged
    ] == [
        "estimate-14:supervisor-route:1",
        "estimate-14:supervisor-route:2",
    ]
    assert current == [later]


def test_conflicting_route_event_id_fails_closed_without_mutation() -> None:
    reducer = _route_event_reducer()
    original = _route_event()
    current = [original]

    with pytest.raises(
        ValueError,
        match="estimate-14:supervisor-route:1",
    ):
        reducer(
            current,
            [
                _route_event(
                    reason="Conflicting route explanation.",
                )
            ],
        )

    assert current == [original]


def test_blank_route_event_id_fails_closed() -> None:
    reducer = _route_event_reducer()

    with pytest.raises(ValueError, match="route_event_id"):
        reducer(
            [],
            [
                _route_event(
                    route_event_id=" ",
                )
            ],
        )
