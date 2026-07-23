"""Hybrid Session 14 supervisor with guarded model-owned routing."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from langgraph.types import Command

from app.generation.graph.ports import SupervisorRouteProposer
from app.generation.graph.review_state import (
    Session14EstimationGraphState,
    SupervisorRouteEvent,
)
from app.schemas.session14_supervision import (
    SupervisorDestination,
    build_supervisor_digest,
)
from app.services.session14_human_review import (
    DEFAULT_SESSION14_CONFIDENCE_THRESHOLD,
    assess_session14_human_review,
)
from app.services.session14_supervision import (
    MAX_ROUTING_STEPS,
    accept_supervisor_proposal,
    deterministic_supervisor_route,
    legal_supervisor_destinations,
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


def build_supervisor_node(
    *,
    route_proposer: SupervisorRouteProposer | None = None,
    confidence_threshold: float = (
        DEFAULT_SESSION14_CONFIDENCE_THRESHOLD
    ),
) -> Session14SupervisorNode:
    """Build the tool-free hybrid Session 14 supervisor."""

    async def supervisor(
        state: Session14EstimationGraphState,
    ) -> Command[SupervisorDestination]:
        estimation_id = _estimation_id(state)
        routing_steps = _routing_steps(state)
        digest = build_supervisor_digest(state)
        max_routing_steps = _max_routing_steps(state)

        if routing_steps >= max_routing_steps:
            guarded_route = deterministic_supervisor_route(
                digest,
                max_routing_steps=max_routing_steps,
                confidence_threshold=confidence_threshold,
                fallback_reason="routing_budget_exhausted",
            )
        elif route_proposer is None:
            guarded_route = deterministic_supervisor_route(
                digest,
                max_routing_steps=max_routing_steps,
                confidence_threshold=confidence_threshold,
            )
        else:
            candidates = legal_supervisor_destinations(
                digest,
                max_routing_steps=max_routing_steps,
                confidence_threshold=confidence_threshold,
            )
            try:
                proposal = await route_proposer.propose_route(
                    digest=digest,
                    candidates=candidates,
                )
            except Exception:
                guarded_route = deterministic_supervisor_route(
                    digest,
                    max_routing_steps=max_routing_steps,
                    confidence_threshold=confidence_threshold,
                    fallback_reason="proposal_failed",
                )
            else:
                guarded_route = accept_supervisor_proposal(
                    proposal,
                    digest,
                    max_routing_steps=max_routing_steps,
                    confidence_threshold=confidence_threshold,
                )

        sequence = routing_steps + 1
        decision = guarded_route.decision
        route_event = SupervisorRouteEvent(
            route_event_id=(
                f"{estimation_id}:supervisor-route:{sequence}"
            ),
            sequence=sequence,
            next_agent=decision.next_agent,
            reason_code=decision.reason_code,
            reason=decision.reason,
            route_source=guarded_route.route_source,
            proposed_agent=guarded_route.proposed_agent,
            valid_candidates=list(
                guarded_route.candidate_agents
            ),
            fallback_reason=guarded_route.fallback_reason,
        )

        update = Session14EstimationGraphState(
            previous_agent=state.get("next_agent"),
            current_agent="supervisor",
            next_agent=decision.next_agent,
            route_reason_code=decision.reason_code,
            routing_steps=sequence,
            route_events=[route_event],
        )

        if decision.next_agent == "human_review_gate":
            assessment = assess_session14_human_review(
                {
                    **dict(state),
                    "route_reason_code": decision.reason_code,
                },
                confidence_threshold=confidence_threshold,
            )
            update.update(
                confidence=assessment.confidence,
                historical_range_status=(
                    assessment.historical_range_status
                ),
                human_review_status="awaiting_human_review",
                human_review_reason_codes=list(
                    assessment.reason_codes
                ),
            )

        return Command(
            goto=decision.next_agent,
            update=update,
        )

    return supervisor
