"""Composable reviewed subgraphs for the Session 13 Plus control room."""

from __future__ import annotations

from typing import Literal

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
from app.generation.graph.nodes.review_policy import (
    build_deterministic_boss_node,
    build_deterministic_critic_node,
)
from app.generation.graph.nodes.structure_review import build_structure_review_node
from app.generation.graph.observability import (
    NOOP_GRAPH_TRACER,
    GraphTracer,
    instrument_graph_node,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.review_state import ReviewedEstimationGraphState
from app.schemas.human_review import HumanReviewMode

REVIEWED_GRAPH_NAME = "session13_plus_reviewed_estimation_graph"
STRUCTURE_SUBGRAPH_NAME = "session13_plus_structure_subgraph"
ESTIMATION_SUBGRAPH_NAME = "session13_plus_estimation_subgraph"
REVIEW_POLICY_SUBGRAPH_NAME = "session13_plus_review_policy_subgraph"


def _structure_route(
    state: ReviewedEstimationGraphState,
) -> Literal["continue", "stop", "regenerate"]:
    return state.get("structure_route", "continue")


def _parent_structure_route(
    state: ReviewedEstimationGraphState,
) -> Literal["continue", "stop"]:
    return "stop" if state.get("structure_route") == "stop" else "continue"


def _instrument(
    *,
    graph_name: str,
    node_name: str,
    node,
    tracer: GraphTracer,
):
    return instrument_graph_node(
        graph_name=graph_name,
        node_name=node_name,
        node=node,
        tracer=tracer,
    )


def build_structure_subgraph(
    dependencies: GraphNodeDependencies,
    *,
    default_review_mode: HumanReviewMode = "risk_based",
    tracer: GraphTracer = NOOP_GRAPH_TRACER,
) -> CompiledStateGraph:
    """Build structure extraction, classification, and durable human review."""

    builder = StateGraph(ReviewedEstimationGraphState)
    builder.add_node(
        "extract_requirements",
        _instrument(
            graph_name=STRUCTURE_SUBGRAPH_NAME,
            node_name="extract_requirements",
            node=build_extract_requirements_node(dependencies),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "classify_components",
        _instrument(
            graph_name=STRUCTURE_SUBGRAPH_NAME,
            node_name="classify_components",
            node=build_classify_components_node(dependencies),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "structure_review",
        _instrument(
            graph_name=STRUCTURE_SUBGRAPH_NAME,
            node_name="structure_review",
            node=build_structure_review_node(default_mode=default_review_mode),
            tracer=tracer,
        ),
    )

    builder.add_edge(START, "extract_requirements")
    builder.add_edge("extract_requirements", "classify_components")
    builder.add_edge("classify_components", "structure_review")
    builder.add_conditional_edges(
        "structure_review",
        _structure_route,
        {
            "continue": END,
            "stop": END,
            "regenerate": "classify_components",
        },
    )
    return builder.compile(name=STRUCTURE_SUBGRAPH_NAME)


def build_estimation_subgraph(
    dependencies: GraphNodeDependencies,
    *,
    tracer: GraphTracer = NOOP_GRAPH_TRACER,
) -> CompiledStateGraph:
    """Build retrieval, deterministic estimation, and invariant validation."""

    builder = StateGraph(ReviewedEstimationGraphState)
    builder.add_node(
        "search_budgets",
        _instrument(
            graph_name=ESTIMATION_SUBGRAPH_NAME,
            node_name="search_budgets",
            node=build_search_budgets_node(dependencies),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "generate_estimate",
        _instrument(
            graph_name=ESTIMATION_SUBGRAPH_NAME,
            node_name="generate_estimate",
            node=build_generate_estimate_node(dependencies),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "validate_and_consolidate",
        _instrument(
            graph_name=ESTIMATION_SUBGRAPH_NAME,
            node_name="validate_and_consolidate",
            node=build_validate_and_consolidate_node(),
            tracer=tracer,
        ),
    )

    builder.add_edge(START, "search_budgets")
    builder.add_edge("search_budgets", "generate_estimate")
    builder.add_edge("generate_estimate", "validate_and_consolidate")
    builder.add_edge("validate_and_consolidate", END)
    return builder.compile(name=ESTIMATION_SUBGRAPH_NAME)


def build_review_policy_subgraph(
    *,
    tracer: GraphTracer = NOOP_GRAPH_TRACER,
) -> CompiledStateGraph:
    """Build typed Critic review followed by deterministic Boss routing."""

    builder = StateGraph(ReviewedEstimationGraphState)
    builder.add_node(
        "deterministic_critic",
        _instrument(
            graph_name=REVIEW_POLICY_SUBGRAPH_NAME,
            node_name="deterministic_critic",
            node=build_deterministic_critic_node(),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "deterministic_boss",
        _instrument(
            graph_name=REVIEW_POLICY_SUBGRAPH_NAME,
            node_name="deterministic_boss",
            node=build_deterministic_boss_node(),
            tracer=tracer,
        ),
    )

    builder.add_edge(START, "deterministic_critic")
    builder.add_edge("deterministic_critic", "deterministic_boss")
    builder.add_edge("deterministic_boss", END)
    return builder.compile(name=REVIEW_POLICY_SUBGRAPH_NAME)


def build_reviewed_estimation_graph(
    dependencies: GraphNodeDependencies,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    default_review_mode: HumanReviewMode = "risk_based",
    tracer: GraphTracer = NOOP_GRAPH_TRACER,
) -> CompiledStateGraph:
    """Compose independently testable structure, estimation, and policy phases."""

    structure_subgraph = build_structure_subgraph(
        dependencies,
        default_review_mode=default_review_mode,
        tracer=tracer,
    )
    estimation_subgraph = build_estimation_subgraph(
        dependencies,
        tracer=tracer,
    )
    review_policy_subgraph = build_review_policy_subgraph(tracer=tracer)

    builder = StateGraph(ReviewedEstimationGraphState)
    builder.add_node("structure_phase", structure_subgraph)
    builder.add_node("estimation_phase", estimation_subgraph)
    builder.add_node("review_policy_phase", review_policy_subgraph)

    builder.add_edge(START, "structure_phase")
    builder.add_conditional_edges(
        "structure_phase",
        _parent_structure_route,
        {
            "continue": "estimation_phase",
            "stop": END,
        },
    )
    builder.add_edge("estimation_phase", "review_policy_phase")
    builder.add_edge("review_policy_phase", END)

    return builder.compile(
        checkpointer=checkpointer,
        name=REVIEWED_GRAPH_NAME,
    )
