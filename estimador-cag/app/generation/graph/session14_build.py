"""Compile the Session 14 Level 1 supervisor graph."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from app.generation.graph.nodes import (
    build_classify_components_node,
    build_extract_requirements_node,
    build_generate_estimate_node,
    build_search_budgets_node,
    build_validate_and_consolidate_node,
)
from app.generation.graph.nodes.session14_supervisor import (
    build_supervisor_node,
)
from app.generation.graph.nodes.session14_workers import (
    Session14WorkerOperation,
    build_budget_searcher_agent,
    build_coherence_validator_agent,
    build_estimate_generator_agent,
    build_requirements_extractor_agent,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.review_state import (
    Session14EstimationGraphState,
)
from app.services.session14_human_review import (
    DEFAULT_SESSION14_CONFIDENCE_THRESHOLD,
)

SESSION14_GRAPH_NAME = "session14_estimation_graph"

SESSION14_NODE_NAMES = (
    "supervisor",
    "requirements_extractor",
    "budget_searcher",
    "estimate_generator",
    "coherence_validator",
    "human_review_gate",
    "finalize",
)

Session14HumanReviewGate = Callable[
    [Session14EstimationGraphState],
    Awaitable[Command[Literal["finalize"]]],
]


def _return_to_supervisor(
    worker: Session14WorkerOperation,
) -> Callable[
    [Session14EstimationGraphState],
    Awaitable[Command[Literal["supervisor"]]],
]:
    async def return_to_supervisor(
        state: Session14EstimationGraphState,
    ) -> Command[Literal["supervisor"]]:
        update = await worker(state)

        return Command(
            goto="supervisor",
            update=update,
        )

    return return_to_supervisor


async def _finalize(
    state: Session14EstimationGraphState,
) -> Command[Literal[END]]:
    update = Session14EstimationGraphState(
        previous_agent=state.get("current_agent"),
        current_agent="finalize",
        next_agent=END,
    )

    return Command(
        goto=END,
        update=update,
    )


def build_session14_estimation_graph(
    dependencies: GraphNodeDependencies,
    *,
    human_review_gate: Session14HumanReviewGate,
    checkpointer: BaseCheckpointSaver | None = None,
    confidence_threshold: float = (
        DEFAULT_SESSION14_CONFIDENCE_THRESHOLD
    ),
) -> CompiledStateGraph:
    """Compile the command-driven Level 1 supervisor workflow."""

    extract_requirements = build_extract_requirements_node(
        dependencies
    )
    classify_components = build_classify_components_node(
        dependencies
    )
    search_budgets = build_search_budgets_node(dependencies)
    generate_estimate = build_generate_estimate_node(dependencies)
    validate_estimate = build_validate_and_consolidate_node()

    requirements_extractor = build_requirements_extractor_agent(
        extract_requirements,
        classify_components,
    )
    budget_searcher = build_budget_searcher_agent(
        search_budgets
    )
    estimate_generator = build_estimate_generator_agent(
        generate_estimate
    )
    coherence_validator = build_coherence_validator_agent(
        validate_estimate
    )

    builder = StateGraph(Session14EstimationGraphState)

    builder.add_node(
        "supervisor",
        build_supervisor_node(
            confidence_threshold=confidence_threshold,
        ),
    )
    builder.add_node(
        "requirements_extractor",
        _return_to_supervisor(requirements_extractor),
    )
    builder.add_node(
        "budget_searcher",
        _return_to_supervisor(budget_searcher),
    )
    builder.add_node(
        "estimate_generator",
        _return_to_supervisor(estimate_generator),
    )
    builder.add_node(
        "coherence_validator",
        _return_to_supervisor(coherence_validator),
    )
    builder.add_node(
        "human_review_gate",
        human_review_gate,
    )
    builder.add_node(
        "finalize",
        _finalize,
    )

    builder.add_edge(START, "supervisor")

    return builder.compile(
        checkpointer=checkpointer,
        name=SESSION14_GRAPH_NAME,
    )
