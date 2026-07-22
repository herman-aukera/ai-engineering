from __future__ import annotations

from copy import deepcopy
from importlib import import_module

import pytest
from langgraph.types import Command

from app.generation.graph.review_state import (
    Session14EstimationGraphState,
)
from app.services import session14_privileges


def _state(
    **overrides: object,
) -> Session14EstimationGraphState:
    state = Session14EstimationGraphState(
        transcript=(
            "CLIENT-SECRET: build an authentication service."
        ),
        estimation_id="estimate-14",
        requirements=[],
        components=[],
        budget_matches=[],
        component_estimates=[],
        requirements_extraction_completed=False,
        budget_search_completed=False,
        validation=None,
        confidence=None,
        review_required=False,
        routing_steps=0,
        max_routing_steps=12,
        current_agent=None,
        previous_agent=None,
        next_agent=None,
        status="pending",
        errors=[],
        trace_events=[],
        agent_contributions=[],
        route_events=[],
    )
    state.update(overrides)
    return state


async def _run_supervisor(
    state: Session14EstimationGraphState,
) -> Command:
    try:
        module = import_module(
            "app.generation.graph.nodes.session14_supervisor"
        )
    except ModuleNotFoundError as exc:
        pytest.fail(
            f"Session 14 supervisor node is missing: {exc}",
            pytrace=False,
        )

    builder = getattr(
        module,
        "build_supervisor_node",
        None,
    )
    assert callable(builder)

    node = builder()
    assert callable(node)

    command = await node(state)

    assert isinstance(command, Command)
    return command


def _command_update(
    command: Command,
) -> dict[str, object]:
    assert isinstance(command.update, dict)
    return command.update


@pytest.mark.asyncio
async def test_supervisor_returns_command_for_first_safe_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization_calls: list[tuple[str, str]] = []

    def deny_tool(
        agent_id: str,
        tool: str,
    ) -> None:
        authorization_calls.append((agent_id, tool))
        raise AssertionError(
            "The supervisor must not execute business tools."
        )

    monkeypatch.setattr(
        session14_privileges,
        "assert_tool_allowed",
        deny_tool,
    )

    state = _state()
    before = deepcopy(state)

    command = await _run_supervisor(state)
    update = _command_update(command)

    route_event = {
        "route_event_id": (
            "estimate-14:supervisor-route:1"
        ),
        "sequence": 1,
        "next_agent": "requirements_extractor",
        "reason_code": "missing_requirements",
        "reason": (
            "Requirements extraction has not completed."
        ),
    }

    assert command.goto == "requirements_extractor"
    assert update == {
        "previous_agent": None,
        "current_agent": "supervisor",
        "next_agent": "requirements_extractor",
        "route_reason_code": "missing_requirements",
        "routing_steps": 1,
        "route_events": [route_event],
    }
    assert authorization_calls == []
    assert state == before
    assert "CLIENT-SECRET" not in str(update)


@pytest.mark.asyncio
async def test_supervisor_routes_generated_estimate_to_validation() -> None:
    state = _state(
        requirements=[
            {
                "requirement_id": "requirement-1",
                "text": "Provide authentication.",
            }
        ],
        components=[
            {
                "component_id": "component-1",
            }
        ],
        requirements_extraction_completed=True,
        budget_search_completed=True,
        component_estimates=[
            {
                "component_id": "component-1",
            }
        ],
        routing_steps=3,
        current_agent="supervisor",
        next_agent="estimate_generator",
    )

    command = await _run_supervisor(state)
    update = _command_update(command)

    assert command.goto == "coherence_validator"
    assert update["previous_agent"] == "estimate_generator"
    assert update["current_agent"] == "supervisor"
    assert update["next_agent"] == "coherence_validator"
    assert update["route_reason_code"] == "missing_validation"
    assert update["routing_steps"] == 4
    assert update["route_events"] == [
        {
            "route_event_id": (
                "estimate-14:supervisor-route:4"
            ),
            "sequence": 4,
            "next_agent": "coherence_validator",
            "reason_code": "missing_validation",
            "reason": (
                "The estimate has not been validated."
            ),
        }
    ]


@pytest.mark.asyncio
async def test_supervisor_routes_completed_work_to_finalize() -> None:
    state = _state(
        requirements=[
            {
                "requirement_id": "requirement-1",
                "text": "Provide authentication.",
            }
        ],
        requirements_extraction_completed=True,
        budget_search_completed=True,
        component_estimates=[
            {
                "component_id": "component-1",
            }
        ],
        validation={
            "is_coherent": True,
            "review_required": False,
            "status": "validated",
        },
        status="validated",
        routing_steps=4,
        current_agent="supervisor",
        next_agent="coherence_validator",
    )

    command = await _run_supervisor(state)
    update = _command_update(command)

    assert command.goto == "finalize"
    assert update["previous_agent"] == "coherence_validator"
    assert update["next_agent"] == "finalize"
    assert update["route_reason_code"] == "work_complete"
    assert update["routing_steps"] == 5


@pytest.mark.asyncio
async def test_supervisor_hop_budget_preempts_more_specialist_work() -> None:
    state = _state(
        routing_steps=3,
        max_routing_steps=3,
        current_agent="supervisor",
        next_agent="budget_searcher",
    )

    command = await _run_supervisor(state)
    update = _command_update(command)

    assert command.goto == "human_review_gate"
    assert update["previous_agent"] == "budget_searcher"
    assert update["next_agent"] == "human_review_gate"
    assert update["route_reason_code"] == (
        "routing_budget_exhausted"
    )
    assert update["routing_steps"] == 4
    assert update["route_events"] == [
        {
            "route_event_id": (
                "estimate-14:supervisor-route:4"
            ),
            "sequence": 4,
            "next_agent": "human_review_gate",
            "reason_code": "routing_budget_exhausted",
            "reason": (
                "The supervisor routing budget is exhausted."
            ),
        }
    ]


@pytest.mark.asyncio
async def test_supervisor_command_is_stable_for_identical_replay() -> None:
    state = _state()
    before = deepcopy(state)

    first = await _run_supervisor(state)
    second = await _run_supervisor(state)

    assert first.goto == second.goto
    assert first.update == second.update
    assert state == before
