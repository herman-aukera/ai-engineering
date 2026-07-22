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
from app.generation.graph.observability import (
    NOOP_GRAPH_TRACER,
    GraphTracer,
    instrument_session14_command_node,
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
    tracer: GraphTracer = NOOP_GRAPH_TRACER,
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
        instrument_session14_command_node(
            graph_name=SESSION14_GRAPH_NAME,
            node_name="supervisor",
            node=build_supervisor_node(
                confidence_threshold=confidence_threshold,
            ),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "requirements_extractor",
        instrument_session14_command_node(
            graph_name=SESSION14_GRAPH_NAME,
            node_name="requirements_extractor",
            node=_return_to_supervisor(
                requirements_extractor
            ),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "budget_searcher",
        instrument_session14_command_node(
            graph_name=SESSION14_GRAPH_NAME,
            node_name="budget_searcher",
            node=_return_to_supervisor(budget_searcher),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "estimate_generator",
        instrument_session14_command_node(
            graph_name=SESSION14_GRAPH_NAME,
            node_name="estimate_generator",
            node=_return_to_supervisor(estimate_generator),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "coherence_validator",
        instrument_session14_command_node(
            graph_name=SESSION14_GRAPH_NAME,
            node_name="coherence_validator",
            node=_return_to_supervisor(coherence_validator),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "human_review_gate",
        instrument_session14_command_node(
            graph_name=SESSION14_GRAPH_NAME,
            node_name="human_review_gate",
            node=human_review_gate,
            tracer=tracer,
        ),
    )
    builder.add_node(
        "finalize",
        instrument_session14_command_node(
            graph_name=SESSION14_GRAPH_NAME,
            node_name="finalize",
            node=_finalize,
            tracer=tracer,
        ),
    )

    builder.add_edge(START, "supervisor")

    return builder.compile(
        checkpointer=checkpointer,
        name=SESSION14_GRAPH_NAME,
    )
