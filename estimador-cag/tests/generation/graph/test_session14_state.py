from __future__ import annotations

from typing import Annotated, get_args, get_origin, get_type_hints

import pytest

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
