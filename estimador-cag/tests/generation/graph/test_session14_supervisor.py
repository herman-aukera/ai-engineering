from __future__ import annotations

from copy import deepcopy
from importlib import import_module

import pytest
from langgraph.types import Command

from app.generation.graph.ports import SupervisorRouteProposer
from app.generation.graph.review_state import (
    Session14EstimationGraphState,
)
from app.schemas.session14_supervision import (
    SupervisorProposalDestination,
    SupervisorRouteProposal,
    SupervisorStateDigest,
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
    *,
    route_proposer: SupervisorRouteProposer | None = None,
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

    node = builder(route_proposer=route_proposer)
    assert callable(node)

    command = await node(state)

    assert isinstance(command, Command)
    return command


class FakeRouteProposer:
    def __init__(
        self,
        next_agent: SupervisorProposalDestination,
        *,
        reason: str = "The proposed specialist can make progress.",
        error: Exception | None = None,
    ) -> None:
        self.next_agent = next_agent
        self.reason = reason
        self.error = error
        self.calls: list[
            tuple[
                SupervisorStateDigest,
                tuple[SupervisorProposalDestination, ...],
            ]
        ] = []

    async def propose_route(
        self,
        *,
        digest: SupervisorStateDigest,
        candidates: tuple[SupervisorProposalDestination, ...],
    ) -> SupervisorRouteProposal:
        self.calls.append((digest, tuple(candidates)))
        if self.error is not None:
            raise self.error
        return SupervisorRouteProposal(
            next_agent=self.next_agent,
            reason=self.reason,
        )


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
        "route_source": "deterministic_policy",
        "proposed_agent": None,
        "valid_candidates": ["requirements_extractor"],
        "fallback_reason": "proposer_unavailable",
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
            "route_source": "deterministic_policy",
            "proposed_agent": None,
            "valid_candidates": ["coherence_validator"],
            "fallback_reason": "proposer_unavailable",
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
            "route_source": "budget_limit",
            "proposed_agent": None,
            "valid_candidates": ["human_review_gate"],
            "fallback_reason": "routing_budget_exhausted",
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


@pytest.mark.asyncio
async def test_supervisor_accepts_legal_typed_model_proposal() -> None:
    proposer = FakeRouteProposer(
        "requirements_extractor",
        reason="Requirements are the first missing dependency.",
    )

    command = await _run_supervisor(
        _state(),
        route_proposer=proposer,
    )
    update = _command_update(command)
    route_event = update["route_events"][0]

    assert command.goto == "requirements_extractor"
    assert route_event["route_source"] == "model"
    assert route_event["proposed_agent"] == (
        "requirements_extractor"
    )
    assert route_event["valid_candidates"] == [
        "requirements_extractor"
    ]
    assert route_event["fallback_reason"] is None
    assert route_event["reason"] == (
        "Requirements are the first missing dependency."
    )
    assert proposer.calls[0][1] == ("requirements_extractor",)


@pytest.mark.asyncio
async def test_supervisor_overrides_illegal_model_proposal() -> None:
    proposer = FakeRouteProposer(
        "finalize",
        reason="Finish immediately.",
    )

    command = await _run_supervisor(
        _state(),
        route_proposer=proposer,
    )
    update = _command_update(command)
    route_event = update["route_events"][0]

    assert command.goto == "requirements_extractor"
    assert route_event["route_source"] == "deterministic_fallback"
    assert route_event["proposed_agent"] == "finalize"
    assert route_event["valid_candidates"] == [
        "requirements_extractor"
    ]
    assert route_event["fallback_reason"] == "illegal_proposal"
    assert route_event["reason_code"] == "missing_requirements"


@pytest.mark.asyncio
async def test_supervisor_falls_back_when_model_proposal_fails() -> None:
    proposer = FakeRouteProposer(
        "requirements_extractor",
        error=RuntimeError("provider unavailable: CLIENT-SECRET"),
    )

    command = await _run_supervisor(
        _state(),
        route_proposer=proposer,
    )
    update = _command_update(command)
    route_event = update["route_events"][0]

    assert command.goto == "requirements_extractor"
    assert route_event["route_source"] == "deterministic_fallback"
    assert route_event["proposed_agent"] is None
    assert route_event["fallback_reason"] == "proposal_failed"
    assert "CLIENT-SECRET" not in str(route_event)


@pytest.mark.asyncio
async def test_supervisor_budget_limit_skips_model_proposer() -> None:
    proposer = FakeRouteProposer("requirements_extractor")

    command = await _run_supervisor(
        _state(
            routing_steps=3,
            max_routing_steps=3,
        ),
        route_proposer=proposer,
    )
    update = _command_update(command)
    route_event = update["route_events"][0]

    assert command.goto == "human_review_gate"
    assert route_event["route_source"] == "budget_limit"
    assert route_event["fallback_reason"] == (
        "routing_budget_exhausted"
    )
    assert proposer.calls == []


@pytest.mark.asyncio
async def test_clean_terminal_state_exposes_two_safe_model_choices() -> None:
    proposer = FakeRouteProposer(
        "human_review_gate",
        reason="Run the deterministic review assessment before exit.",
    )
    state = _state(
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
    )

    command = await _run_supervisor(
        state,
        route_proposer=proposer,
    )
    update = _command_update(command)
    route_event = update["route_events"][0]

    assert command.goto == "human_review_gate"
    assert route_event["reason_code"] == "model_route_accepted"
    assert route_event["valid_candidates"] == [
        "finalize",
        "human_review_gate",
    ]
