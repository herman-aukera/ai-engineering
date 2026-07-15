"""Compile the mandatory Session 13 estimation graph topology."""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.generation.graph.nodes import (
    build_classify_components_node,
    build_extract_requirements_node,
    build_generate_estimate_node,
    build_search_budgets_node,
    build_validate_and_consolidate_node,
)
from app.generation.graph.observability import (
    NOOP_GRAPH_TRACER,
    GraphTracer,
    instrument_graph_node,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.state import EstimationGraphState

GRAPH_NAME = "session13_estimation_graph"

REQUIRED_NODE_NAMES = (
    "extract_requirements",
    "classify_components",
    "search_budgets",
    "generate_estimate",
    "validate_and_consolidate",
)


def build_estimation_graph(
    dependencies: GraphNodeDependencies,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    tracer: GraphTracer = NOOP_GRAPH_TRACER,
) -> CompiledStateGraph:
    """Compile the exact mandatory five-node estimation workflow."""

    (
        extract_requirements,
        classify_components,
        search_budgets,
        generate_estimate,
        validate_and_consolidate,
    ) = REQUIRED_NODE_NAMES

    builder = StateGraph(EstimationGraphState)

    builder.add_node(
        extract_requirements,
        instrument_graph_node(
            graph_name=GRAPH_NAME,
            node_name=extract_requirements,
            node=build_extract_requirements_node(
                dependencies
            ),
            tracer=tracer,
        ),
    )
    builder.add_node(
        classify_components,
        instrument_graph_node(
            graph_name=GRAPH_NAME,
            node_name=classify_components,
            node=build_classify_components_node(
                dependencies
            ),
            tracer=tracer,
        ),
    )
    builder.add_node(
        search_budgets,
        instrument_graph_node(
            graph_name=GRAPH_NAME,
            node_name=search_budgets,
            node=build_search_budgets_node(
                dependencies
            ),
            tracer=tracer,
        ),
    )
    builder.add_node(
        generate_estimate,
        instrument_graph_node(
            graph_name=GRAPH_NAME,
            node_name=generate_estimate,
            node=build_generate_estimate_node(
                dependencies
            ),
            tracer=tracer,
        ),
    )
    builder.add_node(
        validate_and_consolidate,
        instrument_graph_node(
            graph_name=GRAPH_NAME,
            node_name=validate_and_consolidate,
            node=build_validate_and_consolidate_node(),
            tracer=tracer,
        ),
    )

    builder.add_edge(START, extract_requirements)
    builder.add_edge(
        extract_requirements,
        classify_components,
    )
    builder.add_edge(
        classify_components,
        search_budgets,
    )
    builder.add_edge(
        search_budgets,
        generate_estimate,
    )
    builder.add_edge(
        generate_estimate,
        validate_and_consolidate,
    )
    builder.add_edge(
        validate_and_consolidate,
        END,
    )

    return builder.compile(
        checkpointer=checkpointer,
        name=GRAPH_NAME,
    )
