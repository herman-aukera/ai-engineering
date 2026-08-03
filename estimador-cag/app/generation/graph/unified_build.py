"""Canonical semantic consolidation of Session 13 Plus and Session 14 Plus."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from app.generation.graph.nodes import build_validate_and_consolidate_node
from app.generation.graph.nodes.proposal import build_proposal_node
from app.generation.graph.nodes.reformulate_request import (
    build_reformulate_request_node,
)
from app.generation.graph.nodes.reliability_analyst import (
    build_reliability_analyst_node,
)
from app.generation.graph.nodes.review_policy import build_boss_action_node
from app.generation.graph.nodes.semantic_classify import (
    build_semantic_classify_node,
)
from app.generation.graph.nodes.session14_plus_competition import (
    build_session14_plus_competition_node,
)
from app.generation.graph.nodes.session14_plus_human_review import (
    build_context_aware_session14_plus_human_gate,
)
from app.generation.graph.nodes.session14_plus_policy import (
    build_session14_plus_policy_bootstrap_node,
)
from app.generation.graph.nodes.session14_workers import (
    build_coherence_validator_agent,
)
from app.generation.graph.nodes.unified_supervisor import (
    build_unified_supervisor_node,
)
from app.generation.graph.observability import (
    NOOP_GRAPH_TRACER,
    UNIFIED_NODE_SPAN_NAME,
    GraphTracer,
    instrument_graph_node,
    instrument_reviewed_graph_node,
    instrument_session14_command_node,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.reviewed_build import (
    build_estimation_subgraph,
    build_final_recovery_subgraph,
    build_review_policy_subgraph,
    build_structure_subgraph,
)
from app.generation.graph.unified_state import UnifiedEstimationGraphState
from app.schemas.human_review import HumanReviewMode
from app.schemas.session14_plus_policy import (
    ContextDetail,
    ModelCapabilityRegistry,
)
from app.schemas.v3_routing import ExecutionProfileV3
from app.services.selective_recovery import SelectiveRecoveryApplication
from app.services.session14_human_review import (
    DEFAULT_SESSION14_CONFIDENCE_THRESHOLD,
)
from app.services.session14_plus_competition import (
    EstimateCompetitionPolicy,
)

UNIFIED_GRAPH_NAME = "session13_14_plus_unified_graph"
UNIFIED_STRUCTURE_PHASE_NAME = "session13_14_plus_structure_phase"
UNIFIED_NODE_NAMES = (
    "policy_bootstrap",
    "supervisor",
    "structure_phase",
    "estimation_phase",
    "candidate_competition",
    "reliability_analyst",
    "review_policy_phase",
    "boss_action",
    "recovery_phase",
    "coherence_validator",
    "human_review_gate",
    "proposal",
    "finalize",
)

UnifiedHumanReviewGate = Callable[
    [UnifiedEstimationGraphState],
    Awaitable[Command[Literal["finalize"]]],
]


def _instrument_command(
    *,
    node_name: str,
    node,
    tracer: GraphTracer,
):
    return instrument_session14_command_node(
        graph_name=UNIFIED_GRAPH_NAME,
        node_name=node_name,
        node=node,
        tracer=tracer,
        span_name=UNIFIED_NODE_SPAN_NAME,
    )


def build_unified_structure_phase(
    dependencies: GraphNodeDependencies,
    *,
    default_review_mode: HumanReviewMode,
    tracer: GraphTracer,
    semantic_classifier=None,
) -> CompiledStateGraph:
    """Compose reformulation, semantic policy, and editable structure review."""

    structure_core = build_structure_subgraph(
        dependencies,
        default_review_mode=default_review_mode,
        tracer=tracer,
    )
    builder = StateGraph(UnifiedEstimationGraphState)
    builder.add_node(
        "reformulate_request",
        instrument_reviewed_graph_node(
            graph_name=UNIFIED_STRUCTURE_PHASE_NAME,
            node_name="reformulate_request",
            node=build_reformulate_request_node(),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "semantic_classify",
        instrument_reviewed_graph_node(
            graph_name=UNIFIED_STRUCTURE_PHASE_NAME,
            node_name="semantic_classify",
            node=build_semantic_classify_node(classifier=semantic_classifier),
            tracer=tracer,
        ),
    )
    builder.add_node("structure_core", structure_core)
    builder.add_edge(START, "reformulate_request")
    builder.add_edge("reformulate_request", "semantic_classify")
    builder.add_edge("semantic_classify", "structure_core")
    builder.add_edge("structure_core", END)
    return builder.compile(name=UNIFIED_STRUCTURE_PHASE_NAME)


def _phase_marker(
    *,
    flag: str,
    phase: str,
):
    async def mark_phase(
        _state: UnifiedEstimationGraphState,
    ) -> Command[Literal["supervisor"]]:
        return Command(
            goto="supervisor",
            update={flag: True, "unified_phase": phase},
        )

    return mark_phase


def _reviewed_node_to_supervisor(
    node,
    *,
    flag: str,
    phase: str,
):
    async def run_and_return(
        state: UnifiedEstimationGraphState,
    ) -> Command[Literal["supervisor"]]:
        raw_update = await node(state)
        if not isinstance(raw_update, Mapping):
            raise ValueError("reviewed node update must be a mapping")
        return Command(
            goto="supervisor",
            update={**dict(raw_update), flag: True, "unified_phase": phase},
        )

    return run_and_return


def _coherence_to_supervisor(node):
    async def run_and_return(
        state: UnifiedEstimationGraphState,
    ) -> Command[Literal["supervisor"]]:
        update = await node(state)
        return Command(
            goto="supervisor",
            update={
                **dict(update),
                "unified_coherence_completed": True,
                "unified_phase": "coherence",
            },
        )

    return run_and_return


def _recovery_marker():
    async def mark_recovery(
        state: UnifiedEstimationGraphState,
    ) -> Command[Literal["supervisor"]]:
        cycles = int(state.get("unified_recovery_cycles", 0)) + 1
        return Command(
            goto="supervisor",
            update={
                "unified_phase": "recovery",
                "unified_recovery_cycles": cycles,
                "plus_competition_completed": False,
                "plus_competition_candidates": [],
                "plus_competition_assessment": {},
                "unified_reliability_completed": False,
                "reliability_report": {},
                "unified_review_policy_completed": False,
                "critic_report": {},
                "boss_decision": {},
                "boss_route": "final_review",
                "unified_boss_action_completed": False,
                "unified_coherence_completed": False,
            },
        )

    return mark_recovery


def _human_gate_to_proposal(base_gate):
    async def run_gate(
        state: UnifiedEstimationGraphState,
    ) -> Command[Literal["proposal", "finalize"]]:
        command = await base_gate(state)
        raw_update = command.update
        update = dict(raw_update) if isinstance(raw_update, Mapping) else {}
        rejected = update.get("human_review_status") == "rejected"
        return Command(
            goto="finalize" if rejected else "proposal",
            update={**update, "unified_phase": "human_review"},
        )

    return run_gate


async def _finalize(
    state: UnifiedEstimationGraphState,
) -> Command[Literal[END]]:
    return Command(
        goto=END,
        update={
            "unified_phase": "finalized",
            "previous_agent": state.get("current_agent"),
            "current_agent": "finalize",
            "next_agent": END,
        },
    )


def build_unified_estimation_graph(
    dependencies: GraphNodeDependencies,
    *,
    capability_registry: ModelCapabilityRegistry,
    human_review_gate: UnifiedHumanReviewGate,
    repository_state: Mapping[str, str],
    checkpointer: BaseCheckpointSaver | None = None,
    recovery_application: SelectiveRecoveryApplication | None = None,
    tracer: GraphTracer = NOOP_GRAPH_TRACER,
    confidence_threshold: float = DEFAULT_SESSION14_CONFIDENCE_THRESHOLD,
    execution_profile: ExecutionProfileV3 = "balanced",
    context_detail: ContextDetail = "medium",
    competition_policy: EstimateCompetitionPolicy | None = None,
    structure_review_mode: HumanReviewMode = "risk_based",
    retrieval_mode: Literal["sequential", "parallel"] = "parallel",
    retrieval_max_concurrency: int = 4,
    semantic_classifier=None,
) -> CompiledStateGraph:
    """Compile one canonical graph while preserving all older rollback paths."""

    structure_phase = build_unified_structure_phase(
        dependencies,
        default_review_mode=structure_review_mode,
        tracer=tracer,
        semantic_classifier=semantic_classifier,
    )
    estimation_phase = build_estimation_subgraph(
        dependencies,
        recovery_application=recovery_application,
        tracer=tracer,
        retrieval_mode=retrieval_mode,
        retrieval_max_concurrency=retrieval_max_concurrency,
    )
    review_policy_phase = build_review_policy_subgraph(tracer=tracer)
    recovery_phase = build_final_recovery_subgraph(
        dependencies,
        recovery_application=recovery_application,
        tracer=tracer,
    )
    reliability_node = build_reliability_analyst_node()
    boss_action_node = build_boss_action_node()
    proposal_node = build_proposal_node()
    coherence_agent = build_coherence_validator_agent(
        build_validate_and_consolidate_node()
    )
    context_aware_gate = build_context_aware_session14_plus_human_gate(
        human_review_gate,
        default_context_detail=context_detail,
        repository_state=repository_state,
    )

    builder = StateGraph(UnifiedEstimationGraphState)
    builder.add_node(
        "policy_bootstrap",
        instrument_graph_node(
            graph_name=UNIFIED_GRAPH_NAME,
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
        _instrument_command(
            node_name="supervisor",
            node=build_unified_supervisor_node(),
            tracer=tracer,
        ),
    )
    builder.add_node("structure_phase", structure_phase)
    builder.add_node(
        "structure_completed",
        _instrument_command(
            node_name="structure_completed",
            node=_phase_marker(
                flag="unified_structure_completed",
                phase="structure",
            ),
            tracer=tracer,
        ),
    )
    builder.add_node("estimation_phase", estimation_phase)
    builder.add_node(
        "estimation_completed",
        _instrument_command(
            node_name="estimation_completed",
            node=_phase_marker(
                flag="unified_estimation_completed",
                phase="estimation",
            ),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "candidate_competition",
        _instrument_command(
            node_name="candidate_competition",
            node=build_session14_plus_competition_node(
                policy=competition_policy
            ),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "reliability_analyst",
        _instrument_command(
            node_name="reliability_analyst",
            node=_reviewed_node_to_supervisor(
                reliability_node,
                flag="unified_reliability_completed",
                phase="reliability",
            ),
            tracer=tracer,
        ),
    )
    builder.add_node("review_policy_phase", review_policy_phase)
    builder.add_node(
        "review_policy_completed",
        _instrument_command(
            node_name="review_policy_completed",
            node=_phase_marker(
                flag="unified_review_policy_completed",
                phase="review_policy",
            ),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "boss_action",
        _instrument_command(
            node_name="boss_action",
            node=_reviewed_node_to_supervisor(
                boss_action_node,
                flag="unified_boss_action_completed",
                phase="review_policy",
            ),
            tracer=tracer,
        ),
    )
    builder.add_node("recovery_phase", recovery_phase)
    builder.add_node(
        "recovery_completed",
        _instrument_command(
            node_name="recovery_completed",
            node=_recovery_marker(),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "coherence_validator",
        _instrument_command(
            node_name="coherence_validator",
            node=_coherence_to_supervisor(coherence_agent),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "human_review_gate",
        _instrument_command(
            node_name="human_review_gate",
            node=_human_gate_to_proposal(context_aware_gate),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "proposal",
        _instrument_command(
            node_name="proposal",
            node=_reviewed_node_to_supervisor(
                proposal_node,
                flag="unified_proposal_completed",
                phase="proposal",
            ),
            tracer=tracer,
        ),
    )
    builder.add_node(
        "finalize",
        _instrument_command(
            node_name="finalize",
            node=_finalize,
            tracer=tracer,
        ),
    )

    builder.add_edge(START, "policy_bootstrap")
    builder.add_edge("policy_bootstrap", "supervisor")
    builder.add_edge("structure_phase", "structure_completed")
    builder.add_edge("estimation_phase", "estimation_completed")
    builder.add_edge("review_policy_phase", "review_policy_completed")
    builder.add_edge("recovery_phase", "recovery_completed")

    return builder.compile(
        checkpointer=checkpointer,
        name=UNIFIED_GRAPH_NAME,
    )
