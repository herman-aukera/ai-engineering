"""Task 14 specialist adapters over inherited Session 13 nodes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from copy import deepcopy

from app.generation.graph.review_state import (
    AgentContribution,
    Session14EstimationGraphState,
)
from app.generation.graph.state import ComponentItem
from app.services.session14_privileges import assert_tool_allowed

Session14WorkerOperation = Callable[
    [Session14EstimationGraphState],
    Awaitable[Session14EstimationGraphState],
]


def _required_components(
    state: Session14EstimationGraphState,
) -> list[ComponentItem]:
    components = state.get("components")

    if not isinstance(components, list) or not components:
        raise ValueError(
            "budget_searcher requires classified components"
        )

    return components


def _routing_sequence(
    state: Session14EstimationGraphState,
) -> int:
    sequence = state.get("routing_steps")

    if (
        isinstance(sequence, bool)
        or not isinstance(sequence, int)
        or sequence < 0
    ):
        raise ValueError("routing_steps must be a non-negative integer")

    return sequence


def _estimation_id(
    state: Session14EstimationGraphState,
) -> str:
    estimation_id = state.get("estimation_id")

    if not isinstance(estimation_id, str) or not estimation_id.strip():
        raise ValueError("estimation_id must not be blank")

    return estimation_id.strip()


def _budget_tool_state(
    state: Session14EstimationGraphState,
    *,
    components: list[ComponentItem],
) -> Session14EstimationGraphState:
    existing_matches = state.get("budget_matches", [])
    execution_metadata = state.get("execution_metadata", {})

    if not isinstance(existing_matches, list):
        raise ValueError("budget_matches must be a list")

    if not isinstance(execution_metadata, Mapping):
        raise ValueError("execution_metadata must be a mapping")

    return Session14EstimationGraphState(
        components=deepcopy(components),
        budget_matches=deepcopy(existing_matches),
        execution_metadata=deepcopy(dict(execution_metadata)),
    )


def build_budget_searcher_agent(
    search_budgets: Session14WorkerOperation,
) -> Session14WorkerOperation:
    """Wrap inherited retrieval as a least-privilege Task 14 specialist."""

    async def budget_searcher(
        state: Session14EstimationGraphState,
    ) -> Session14EstimationGraphState:
        components = _required_components(state)

        assert_tool_allowed(
            "budget_searcher",
            "search_budgets",
        )

        raw_update = await search_budgets(
            _budget_tool_state(
                state,
                components=components,
            )
        )

        if not isinstance(raw_update, Mapping):
            raise ValueError(
                "search_budgets must return a partial state mapping"
            )

        update = Session14EstimationGraphState(
            **deepcopy(dict(raw_update))
        )
        matches = update.get("budget_matches")

        if not isinstance(matches, list):
            raise ValueError(
                "search_budgets update must contain budget_matches"
            )

        update["budget_search_completed"] = True

        sequence = _routing_sequence(state)
        match_count = len(matches)
        match_word = "match" if match_count == 1 else "matches"
        state_delta_keys = sorted(
            {
                *update.keys(),
                "agent_contributions",
            }
        )

        contribution = AgentContribution(
            contribution_id=(
                f"{_estimation_id(state)}:"
                f"budget_searcher:{sequence}"
            ),
            agent_id="budget_searcher",
            sequence=sequence,
            summary=(
                f"Budget search completed with "
                f"{match_count} {match_word}."
            ),
            state_delta_keys=state_delta_keys,
        )
        update["agent_contributions"] = [contribution]

        return update

    return budget_searcher
