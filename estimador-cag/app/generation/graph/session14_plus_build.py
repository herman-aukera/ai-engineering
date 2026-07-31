"""Additive Session 14 Plus graph with policy, context, and competition."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
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
from app.generation.graph.nodes.session14_plus_competition import (
    build_session14_plus_competition_node,
)
from app.generation.graph.nodes.session14_plus_policy import (
    build_session14_plus_policy_bootstrap_node,
    build_session14_plus_supervisor_node,
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
    instrument_graph_node,
    instrument_session14_command_node,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.session14_plus_state import (
    Session14PlusEstimationGraphState,
)
from app.schemas.session14_plus_policy import (
    ContextDetail,
    ModelCapabilityRegistry,
)
from app.schemas.v3_routing import ExecutionProfileV3
from app.services.session14_human_review import (
    DEFAULT_SESSION14_CONFIDENCE_THRESHOLD,
)
from app.services.session14_plus_competition import (
    EstimateCompetitionPolicy,
)

SESSION14_PLUS_GRAPH_NAME = "session14_plus_estimation_graph"
SESSION14_PLUS_NODE_NAMES = (
    "policy_bootstrap",
    "supervisor",
    "requirements_extractor",
    "budget_searcher",
    "estimate_generator",
    "candidate_competition",
    "coherence_validator",
    "human_review_gate",
    "finalize",
)

Session14PlusHumanReviewGate = Callable[
    [Session14PlusEstimationGraphState],
    Awaitable[Command[Literal["finalize"]]],
]


def _return_to_supervisor(
    worker: Session14WorkerOperation,
) -> Callable[
    [Session14PlusEstimationGraphState],
    Awaitable[Command[Literal["supervisor"]]],
]:
    async def return_to_supervisor(
        state: Session14PlusEstimationGraphState,
    ) -> Command[Literal["supervisor"]]:
        update = await worker(state)
        return Command(goto="supervisor", update=update)

    return return_to_supervisor


def _return_to_candidate_competition(
    worker: Session14WorkerOperation,
) -> Callable[
    [Session14PlusEstimationGraphState],
    Awaitable[Command[Literal["candidate_competition"]]],
]:
    async def return_to_candidate_competition(
        state: Session14PlusEstimationGraphState,
    ) -> Command[Literal["candidate_competition"]]:
        update = await worker(state)
        return Command(goto="candidate_competition", update=update)

    return return_to_candidate_competition


async def _finalize(
    state: Session14PlusEstimationGraphState,
) -> Command[Literal[END]]:
    return Command(
        goto=END,
        update=Session14PlusEstimationGraphState(
            previous_agent=state.get("current_agent"),
            current_agent="finalize",
            next_agent=END,
        ),
    )


def build_session14_plus_estimation_graph(
    dependencies: GraphNodeDependencies,
    *,
    capability_registry: ModelCapabilityRegistry,
    human_review_gate: Session14PlusHumanReviewGate,
    repository_state: Mapping[str, str],
    checkpointer: BaseCheckpointSaver | None = None,
    tracer: GraphTracer = NOOP_GRAPH_TRACER,
    confidence_threshold: float = DEFAULT_SESSION14_CONFIDENCE_THRESHOLD,
    execution_profile: ExecutionProfileV3 = "balanced",
    context_detail: ContextDetail = "medium",
    competition_policy: EstimateCompetitionPolicy | None = None,
) -> CompiledStateGraph:
    """Compile the Plus graph without modifying the submitted Session 14 graph."""

    extract_requirements = build_extract_requirements_node(dependencies)
    classify_components = build_classify_components_node(dependencies)
    search_budgets = build_search_budgets_node(dependencies)
    generate_estimate = build_generate_estimate_node(dependencies)
    validate_estimate = build_validate_and_consolidate_node()

    requirements_extractor = build_requirements_extractor_agent(
        extract_requirements,
        classify_components,
    )
    budget_searcher = build_budget_searcher_agent(search_budgets)
    estimate_generator = build_estimate_generator_agent(generate_estimate)
    coherence_validator = build_coherence_validator_agent(validate_estimate)

    builder = StateGraph(Session14PlusEstimationGraphState)
    builder.add_node(
        "policy_bootstrap",
        instrument_graph_node(
            graph_name=SESSION14_PLUS_GRAPH_NAME,
            node_name="policy_bootstrap",
            node=build_session14_plus_policy_bootstrap_node(
                capability_registry=capability_registry,
                execution_profile=execution_profile,
                context_detail=context_detail,
                repository_state=repository_state,
            ),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "supervisor",
        instrument_session14_command_node(
            graph_name=SESSION14_PLUS_GRAPH_NAME,
            node_name="supervisor",
            node=build_session14_plus_supervisor_node(
                context_detail=context_detail,
                repository_state=repository_state,
                route_proposer=dependencies.supervisor_route_proposer,
                confidence_threshold=confidence_threshold,
            ),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "requirements_extractor",
        instrument_session14_command_node(
            graph_name=SESSION14_PLUS_GRAPH_NAME,
            node_name="requirements_extractor",
            node=_return_to_supervisor(requirements_extractor),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "budget_searcher",
        instrument_session14_command_node(
            graph_name=SESSION14_PLUS_GRAPH_NAME,
            node_name="budget_searcher",
            node=_return_to_supervisor(budget_searcher),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "estimate_generator",
        instrument_session14_command_node(
            graph_name=SESSION14_PLUS_GRAPH_NAME,
            node_name="estimate_generator",
            node=_return_to_candidate_competition(estimate_generator),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "candidate_competition",
        instrument_session14_command_node(
            graph_name=SESSION14_PLUS_GRAPH_NAME,
            node_name="candidate_competition",
            node=build_session14_plus_competition_node(
                policy=competition_policy
            ),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "coherence_validator",
        instrument_session14_command_node(
            graph_name=SESSION14_PLUS_GRAPH_NAME,
            node_name="coherence_validator",
            node=_return_to_supervisor(coherence_validator),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "human_review_gate",
        instrument_session14_command_node(
            graph_name=SESSION14_PLUS_GRAPH_NAME,
            node_name="human_review_gate",
            node=human_review_gate,
            tracer=tracer,
        ),
    )
    builder.add_node(
        "finalize",
        instrument_session14_command_node(
            graph_name=SESSION14_PLUS_GRAPH_NAME,
            node_name="finalize",
            node=_finalize,
            tracer=tracer,
        ),
    )

    builder.add_edge(START, "policy_bootstrap")
    builder.add_edge("policy_bootstrap", "supervisor")

    return builder.compile(
        checkpointer=checkpointer,
        name=SESSION14_PLUS_GRAPH_NAME,
    )
