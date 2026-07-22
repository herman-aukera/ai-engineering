"""Deterministic Session 14 supervisor with explicit LangGraph routing."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from langgraph.types import Command

from app.generation.graph.review_state import (
    Session14EstimationGraphState,
    SupervisorRouteEvent,
)
from app.schemas.session14_supervision import SupervisorDestination, build_supervisor_digest
from app.services.session14_supervision import (
    MAX_ROUTING_STEPS,
    choose_deterministic_route,
)

Session14SupervisorNode = Callable[
    [Session14EstimationGraphState],
    Awaitable[Command[SupervisorDestination]],
]


def _estimation_id(
    state: Session14EstimationGraphState,
) -> str:
    estimation_id = state.get("estimation_id")

    if not isinstance(estimation_id, str) or not estimation_id.strip():
        raise ValueError("estimation_id must not be blank")

    return estimation_id.strip()


def _routing_steps(
    state: Session14EstimationGraphState,
) -> int:
    routing_steps = state.get("routing_steps", 0)

    if (
        isinstance(routing_steps, bool)
        or not isinstance(routing_steps, int)
        or routing_steps < 0
    ):
        raise ValueError(
            "routing_steps must be a non-negative integer"
        )

    return routing_steps


def _max_routing_steps(
    state: Session14EstimationGraphState,
) -> int:
    max_routing_steps = state.get(
        "max_routing_steps",
        MAX_ROUTING_STEPS,
    )

    if (
        isinstance(max_routing_steps, bool)
        or not isinstance(max_routing_steps, int)
        or max_routing_steps < 1
    ):
        raise ValueError(
            "max_routing_steps must be a positive integer"
        )

    return max_routing_steps


def build_supervisor_node() -> Session14SupervisorNode:
    """Build the tool-free deterministic Session 14 supervisor."""

    async def supervisor(
        state: Session14EstimationGraphState,
    ) -> Command[SupervisorDestination]:
        estimation_id = _estimation_id(state)
        routing_steps = _routing_steps(state)
        digest = build_supervisor_digest(state)

        decision = choose_deterministic_route(
            digest,
            max_routing_steps=_max_routing_steps(state),
        )

        sequence = routing_steps + 1
        route_event = SupervisorRouteEvent(
            route_event_id=(
                f"{estimation_id}:supervisor-route:{sequence}"
            ),
            sequence=sequence,
            next_agent=decision.next_agent,
            reason_code=decision.reason_code,
            reason=decision.reason,
        )

        update = Session14EstimationGraphState(
            previous_agent=state.get("next_agent"),
            current_agent="supervisor",
            next_agent=decision.next_agent,
            route_reason_code=decision.reason_code,
            routing_steps=sequence,
            route_events=[route_event],
        )

        return Command(
            goto=decision.next_agent,
            update=update,
        )

    return supervisor
