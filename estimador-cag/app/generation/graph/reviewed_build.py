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
)
from app.generation.graph.nodes.final_estimate_review import (
    build_final_estimate_review_node,
)
from app.generation.graph.nodes.parallel_retrieval import (
    build_parallel_retrieval_nodes,
    parallel_retrieval_dispatch,
)
from app.generation.graph.nodes.review_policy import (
    build_deterministic_boss_node,
    build_deterministic_critic_node,
)
from app.generation.graph.nodes.reviewed_validation import (
    build_reviewed_validation_node,
)
from app.generation.graph.nodes.selective_recovery import (
    build_selective_recovery_node,
)
from app.generation.graph.nodes.structure_review import build_structure_review_node
from app.generation.graph.observability import (
    NOOP_GRAPH_TRACER,
    GraphTracer,
    instrument_reviewed_graph_node,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.review_state import ReviewedEstimationGraphState
from app.schemas.human_review import HumanReviewMode
from app.services.selective_recovery import SelectiveRecoveryApplication

REVIEWED_GRAPH_NAME = "session13_plus_reviewed_estimation_graph"
STRUCTURE_SUBGRAPH_NAME = "session13_plus_structure_subgraph"
ESTIMATION_SUBGRAPH_NAME = "session13_plus_estimation_subgraph"
REVIEW_POLICY_SUBGRAPH_NAME = "session13_plus_review_policy_subgraph"
FINAL_RECOVERY_SUBGRAPH_NAME = "session13_plus_final_recovery_subgraph"


def _structure_route(
    state: ReviewedEstimationGraphState,
) -> Literal["continue", "stop", "regenerate"]:
    return state.get("structure_route", "continue")


def _parent_structure_route(
    state: ReviewedEstimationGraphState,
) -> Literal["continue", "stop"]:
    return "stop" if state.get("structure_route") == "stop" else "continue"


def _recovery_route(
    state: ReviewedEstimationGraphState,
) -> Literal["complete", "recalculate"]:
    return state.get("recovery_route", "complete")


def _final_review_route(
    state: ReviewedEstimationGraphState,
) -> Literal["complete", "stop", "recover"]:
    return state.get("final_review_route", "complete")


def _instrument(
    *,
    graph_name: str,
    node_name: str,
    node,
    tracer: GraphTracer,
):
    return instrument_reviewed_graph_node(
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
    recovery_application: SelectiveRecoveryApplication | None = None,
    tracer: GraphTracer = NOOP_GRAPH_TRACER,
    retrieval_mode: Literal["sequential", "parallel"] = "sequential",
    retrieval_max_concurrency: int = 4,
) -> CompiledStateGraph:
    """Build deterministic estimation plus selective evidence recovery."""

    builder = StateGraph(ReviewedEstimationGraphState)
    if retrieval_mode == "sequential":
        builder.add_node(
            "search_budgets",
            _instrument(
                graph_name=ESTIMATION_SUBGRAPH_NAME,
                node_name="search_budgets",
                node=build_search_budgets_node(dependencies),
                tracer=tracer,
            ),
        )
    else:
        fan_out, worker, fan_in = build_parallel_retrieval_nodes(
            dependencies, max_concurrency=retrieval_max_concurrency
        )
        builder.add_node(
            "parallel_retrieval_dispatch",
            _instrument(
                graph_name=ESTIMATION_SUBGRAPH_NAME,
                node_name="parallel_retrieval_dispatch",
                node=parallel_retrieval_dispatch,
                tracer=tracer,
            ),
        )
        builder.add_node(
            "parallel_retrieval_worker",
            _instrument(
                graph_name=ESTIMATION_SUBGRAPH_NAME,
                node_name="parallel_retrieval_worker",
                node=worker,
                tracer=tracer,
            ),
        )
        builder.add_node(
            "parallel_retrieval_merge",
            _instrument(
                graph_name=ESTIMATION_SUBGRAPH_NAME,
                node_name="parallel_retrieval_merge",
                node=fan_in,
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
        "validate_initial",
        _instrument(
            graph_name=ESTIMATION_SUBGRAPH_NAME,
            node_name="validate_initial",
            node=build_reviewed_validation_node(rebuild_aggregate=False),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "selective_recovery",
        _instrument(
            graph_name=ESTIMATION_SUBGRAPH_NAME,
            node_name="selective_recovery",
            node=build_selective_recovery_node(recovery_application),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "recalculate_estimate",
        _instrument(
            graph_name=ESTIMATION_SUBGRAPH_NAME,
            node_name="recalculate_estimate",
            node=build_generate_estimate_node(dependencies),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "validate_final",
        _instrument(
            graph_name=ESTIMATION_SUBGRAPH_NAME,
            node_name="validate_final",
            node=build_reviewed_validation_node(rebuild_aggregate=True),
            tracer=tracer,
        ),
    )

    if retrieval_mode == "sequential":
        builder.add_edge(START, "search_budgets")
        builder.add_edge("search_budgets", "generate_estimate")
    else:
        builder.add_edge(START, "parallel_retrieval_dispatch")
        builder.add_conditional_edges("parallel_retrieval_dispatch", fan_out)
        builder.add_edge("parallel_retrieval_worker", "parallel_retrieval_merge")
        builder.add_edge("parallel_retrieval_merge", "generate_estimate")
    builder.add_edge("generate_estimate", "validate_initial")
    builder.add_edge("validate_initial", "selective_recovery")
    builder.add_conditional_edges(
        "selective_recovery",
        _recovery_route,
        {
            "complete": END,
            "recalculate": "recalculate_estimate",
        },
    )
    builder.add_edge("recalculate_estimate", "validate_final")
    builder.add_edge("validate_final", END)
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


def build_final_recovery_subgraph(
    dependencies: GraphNodeDependencies,
    *,
    recovery_application: SelectiveRecoveryApplication | None,
    tracer: GraphTracer = NOOP_GRAPH_TRACER,
) -> CompiledStateGraph:
    """Run only selective recovery and deterministic recalculation after review."""

    builder = StateGraph(ReviewedEstimationGraphState)
    builder.add_node(
        "human_requested_recovery",
        _instrument(
            graph_name=FINAL_RECOVERY_SUBGRAPH_NAME,
            node_name="human_requested_recovery",
            node=build_selective_recovery_node(recovery_application),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "human_requested_recalculation",
        _instrument(
            graph_name=FINAL_RECOVERY_SUBGRAPH_NAME,
            node_name="human_requested_recalculation",
            node=build_generate_estimate_node(dependencies),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "human_requested_validation",
        _instrument(
            graph_name=FINAL_RECOVERY_SUBGRAPH_NAME,
            node_name="human_requested_validation",
            node=build_reviewed_validation_node(rebuild_aggregate=True),
            tracer=tracer,
        ),
    )
    builder.add_edge(START, "human_requested_recovery")
    builder.add_conditional_edges(
        "human_requested_recovery",
        _recovery_route,
        {"complete": END, "recalculate": "human_requested_recalculation"},
    )
    builder.add_edge("human_requested_recalculation", "human_requested_validation")
    builder.add_edge("human_requested_validation", END)
    return builder.compile(name=FINAL_RECOVERY_SUBGRAPH_NAME)


def build_reviewed_estimation_graph(
    dependencies: GraphNodeDependencies,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    default_review_mode: HumanReviewMode = "risk_based",
    recovery_application: SelectiveRecoveryApplication | None = None,
    tracer: GraphTracer = NOOP_GRAPH_TRACER,
    retrieval_mode: Literal["sequential", "parallel"] = "sequential",
    retrieval_max_concurrency: int = 4,
) -> CompiledStateGraph:
    """Compose independently testable structure, estimation, and policy phases."""

    structure_subgraph = build_structure_subgraph(
        dependencies,
        default_review_mode=default_review_mode,
        tracer=tracer,
    )
    estimation_subgraph = build_estimation_subgraph(
        dependencies,
        recovery_application=recovery_application,
        tracer=tracer,
        retrieval_mode=retrieval_mode,
        retrieval_max_concurrency=retrieval_max_concurrency,
    )
    review_policy_subgraph = build_review_policy_subgraph(tracer=tracer)
    final_recovery_subgraph = build_final_recovery_subgraph(
        dependencies,
        recovery_application=recovery_application,
        tracer=tracer,
    )

    builder = StateGraph(ReviewedEstimationGraphState)
    builder.add_node("structure_phase", structure_subgraph)
    builder.add_node("estimation_phase", estimation_subgraph)
    builder.add_node("review_policy_phase", review_policy_subgraph)
    builder.add_node(
        "final_estimate_review",
        _instrument(
            graph_name=REVIEWED_GRAPH_NAME,
            node_name="final_estimate_review",
            node=build_final_estimate_review_node(),
            tracer=tracer,
        ),
    )
    builder.add_node("final_recovery_phase", final_recovery_subgraph)
    builder.add_node(
        "final_consolidation",
        _instrument(
            graph_name=REVIEWED_GRAPH_NAME,
            node_name="final_consolidation",
            node=build_reviewed_validation_node(rebuild_aggregate=True),
            tracer=tracer,
        ),
    )

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
    builder.add_edge("review_policy_phase", "final_estimate_review")
    builder.add_conditional_edges(
        "final_estimate_review",
        _final_review_route,
        {
            "complete": "final_consolidation",
            "stop": END,
            "recover": "final_recovery_phase",
        },
    )
    builder.add_edge("final_recovery_phase", "review_policy_phase")
    builder.add_edge("final_consolidation", END)

    return builder.compile(
        checkpointer=checkpointer,
        name=REVIEWED_GRAPH_NAME,
    )
