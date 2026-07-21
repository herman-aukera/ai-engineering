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

def _worker_execution_metadata(
    state: Session14EstimationGraphState,
    *,
    operation: str,
) -> dict[str, object]:
    metadata = state.get("execution_metadata", {})

    if not isinstance(metadata, Mapping):
        raise ValueError(
            f"{operation} requires execution_metadata to be a mapping"
        )

    return deepcopy(dict(metadata))


def _copy_worker_update(
    raw_update: object,
    *,
    operation: str,
) -> Session14EstimationGraphState:
    if not isinstance(raw_update, Mapping):
        raise ValueError(
            f"{operation} must return a partial state mapping"
        )

    return Session14EstimationGraphState(
        **deepcopy(dict(raw_update))
    )


def _merge_serial_worker_updates(
    extraction_update: Session14EstimationGraphState,
    classification_update: Session14EstimationGraphState,
) -> Session14EstimationGraphState:
    update = Session14EstimationGraphState(
        **deepcopy(dict(extraction_update))
    )

    for key, value in classification_update.items():
        if key not in {
            "errors",
            "execution_metadata",
            "trace_events",
        }:
            update[key] = deepcopy(value)

    for key in ("errors", "trace_events"):
        if key not in extraction_update and key not in classification_update:
            continue

        extraction_items = extraction_update.get(key, [])
        classification_items = classification_update.get(key, [])

        if not isinstance(extraction_items, list) or not isinstance(
            classification_items,
            list,
        ):
            raise ValueError(f"worker update {key} must be a list")

        update[key] = deepcopy(
            [*extraction_items, *classification_items]
        )

    if (
        "execution_metadata" in extraction_update
        or "execution_metadata" in classification_update
    ):
        update["execution_metadata"] = {
            **_worker_execution_metadata(
                extraction_update,
                operation="extract_requirements",
            ),
            **_worker_execution_metadata(
                classification_update,
                operation="classify_components",
            ),
        }

    return update


def build_requirements_extractor_agent(
    extract_requirements: Session14WorkerOperation,
    classify_components: Session14WorkerOperation,
) -> Session14WorkerOperation:
    """Compose inherited extraction and classification with bounded context."""

    async def requirements_extractor(
        state: Session14EstimationGraphState,
    ) -> Session14EstimationGraphState:
        extraction_state = Session14EstimationGraphState(
            execution_metadata=_worker_execution_metadata(
                state,
                operation="extract_requirements",
            )
        )
        if "transcript" in state:
            extraction_state["transcript"] = deepcopy(
                state["transcript"]
            )

        extraction_update = _copy_worker_update(
            await extract_requirements(extraction_state),
            operation="extract_requirements",
        )
        requirements = extraction_update.get("requirements")

        if not isinstance(requirements, list):
            raise ValueError(
                "extract_requirements update must contain requirements"
            )

        if not requirements:
            update = Session14EstimationGraphState(
                **deepcopy(dict(extraction_update))
            )
            update["components"] = []
            update["review_required"] = True
            update["requirements_extraction_completed"] = False
            summary = (
                "Requirement extraction produced no usable requirements; "
                "component classification was skipped."
            )
        else:
            classification_state = Session14EstimationGraphState(
                requirements=deepcopy(requirements),
                execution_metadata=_worker_execution_metadata(
                    extraction_update,
                    operation="classify_components",
                ),
            )
            classification_update = _copy_worker_update(
                await classify_components(classification_state),
                operation="classify_components",
            )
            components = classification_update.get("components")

            if not isinstance(components, list):
                raise ValueError(
                    "classify_components update must contain components"
                )

            update = _merge_serial_worker_updates(
                extraction_update,
                classification_update,
            )
            stage_completed = bool(components)
            update["requirements_extraction_completed"] = stage_completed

            requirement_count = len(requirements)
            requirement_word = (
                "requirement"
                if requirement_count == 1
                else "requirements"
            )

            if stage_completed:
                component_count = len(components)
                component_word = (
                    "component"
                    if component_count == 1
                    else "components"
                )
                summary = (
                    f"Extracted {requirement_count} {requirement_word} and "
                    f"classified {component_count} {component_word}."
                )
            else:
                update["review_required"] = True
                summary = (
                    f"Extracted {requirement_count} {requirement_word}, but "
                    "component classification produced no usable components."
                )

        sequence = _routing_sequence(state)
        contribution = AgentContribution(
            contribution_id=(
                f"{_estimation_id(state)}:"
                f"requirements_extractor:{sequence}"
            ),
            agent_id="requirements_extractor",
            sequence=sequence,
            summary=summary,
            state_delta_keys=sorted(
                {
                    *update.keys(),
                    "agent_contributions",
                }
            ),
        )
        update["agent_contributions"] = [contribution]

        return update

    return requirements_extractor

def _estimate_tool_state(
    state: Session14EstimationGraphState,
    *,
    components: list[ComponentItem],
) -> Session14EstimationGraphState:
    budget_matches = state.get("budget_matches", [])

    if not isinstance(budget_matches, list):
        raise ValueError(
            "estimate_generator requires budget_matches to be a list"
        )

    return Session14EstimationGraphState(
        components=deepcopy(components),
        budget_matches=deepcopy(budget_matches),
        execution_metadata=_worker_execution_metadata(
            state,
            operation="calculate_estimate",
        ),
    )


def build_estimate_generator_agent(
    calculate_estimate: Session14WorkerOperation,
) -> Session14WorkerOperation:
    """Wrap deterministic estimation with least-privilege context."""

    async def estimate_generator(
        state: Session14EstimationGraphState,
    ) -> Session14EstimationGraphState:
        components = state.get("components")

        if not isinstance(components, list) or not components:
            raise ValueError(
                "estimate_generator requires classified components"
            )

        if state.get("budget_search_completed") is not True:
            raise ValueError(
                "estimate_generator requires a completed budget search"
            )

        assert_tool_allowed(
            "estimate_generator",
            "calculate_estimate",
        )

        update = _copy_worker_update(
            await calculate_estimate(
                _estimate_tool_state(
                    state,
                    components=components,
                )
            ),
            operation="calculate_estimate",
        )
        component_estimates = update.get("component_estimates")

        if not isinstance(component_estimates, list):
            raise ValueError(
                "calculate_estimate update must contain "
                "component_estimates"
            )

        sequence = _routing_sequence(state)
        estimate_count = len(component_estimates)
        estimate_word = (
            "estimate" if estimate_count == 1 else "estimates"
        )

        contribution = AgentContribution(
            contribution_id=(
                f"{_estimation_id(state)}:"
                f"estimate_generator:{sequence}"
            ),
            agent_id="estimate_generator",
            sequence=sequence,
            summary=(
                f"Generated {estimate_count} "
                f"component {estimate_word}."
            ),
            state_delta_keys=sorted(
                {
                    *update.keys(),
                    "agent_contributions",
                }
            ),
        )
        update["agent_contributions"] = [contribution]

        return update

    return estimate_generator
