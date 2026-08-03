"""Checkpoint-safe state shared by reviewed and supervised graph variants."""

from __future__ import annotations

import operator
from typing import Annotated, Literal, NotRequired, TypedDict

from app.generation.graph.state import (
    EstimationGraphState,
    new_estimation_graph_state,
)
from app.schemas.human_review import HumanReviewMode
from app.schemas.session14_human_review import (
    HistoricalRangeStatus,
    Session14HumanReviewActionRecord,
    Session14HumanReviewReasonCode,
    Session14HumanReviewStatus,
)
from app.schemas.session14_supervision import (
    RouteReasonCode,
    SupervisorDestination,
    SupervisorFallbackReason,
    SupervisorProposalDestination,
    SupervisorRouteSource,
)

StructureReviewStatus = Literal[
    "not_requested",
    "skipped",
    "approved",
    "edited",
    "rejected",
    "regeneration_requested",
]
StructureRoute = Literal["continue", "stop", "regenerate"]
RecoveryStatus = Literal[
    "not_requested",
    "skipped",
    "completed",
    "partial",
    "failed",
]
RecoveryRoute = Literal["complete", "recalculate"]
FinalReviewRoute = Literal["complete", "stop", "recover"]
BossRoute = Literal["final_review", "recover", "stop"]

Session14AgentId = Literal[
    "supervisor",
    "requirements_extractor",
    "budget_searcher",
    "estimate_generator",
    "coherence_validator",
    "human_review_gate",
    "finalize",
]


def merge_parallel_retrieval_results(
    current: list[dict[str, object]],
    incoming: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Merge replayed worker envelopes once, independent of completion order."""

    by_component = {
        str(item.get("component_id")): dict(item)
        for item in [*current, *incoming]
        if item.get("component_id") is not None
    }
    return sorted(
        by_component.values(),
        key=lambda item: (
            int(item.get("component_index", 0)),
            str(item.get("component_id", "")),
        ),
    )


class StructureReviewRecord(TypedDict, total=False):
    action: str
    reason: str | None
    revision: int


class AgentContribution(TypedDict):
    """One replay-safe, sanitized specialist contribution."""

    contribution_id: str
    agent_id: Session14AgentId
    sequence: int
    summary: str
    state_delta_keys: list[str]
    action: NotRequired[str]
    tool_name: NotRequired[
        Literal[
            "search_budgets",
            "calculate_estimate",
            "validate_estimate",
        ]
        | None
    ]
    privilege_decision: NotRequired[
        Literal["allowed", "not_applicable", "denied"]
    ]
    execution_status: NotRequired[
        Literal["succeeded", "denied", "failed"]
    ]
    validated_input_shape: NotRequired[dict[str, str]]
    result_ref: NotRequired[str | None]
    duration_ms: NotRequired[int]


class SupervisorRouteEvent(TypedDict):
    """One replay-safe, sanitized supervisor routing decision."""

    route_event_id: str
    sequence: int
    next_agent: SupervisorDestination
    reason_code: RouteReasonCode
    reason: str
    route_source: NotRequired[SupervisorRouteSource]
    proposed_agent: NotRequired[
        SupervisorProposalDestination | None
    ]
    valid_candidates: NotRequired[
        list[SupervisorProposalDestination]
    ]
    fallback_reason: NotRequired[
        SupervisorFallbackReason | None
    ]


def merge_session14_human_review_actions(
    current: list[Session14HumanReviewActionRecord],
    incoming: list[Session14HumanReviewActionRecord],
) -> list[Session14HumanReviewActionRecord]:
    """Deduplicate identical actions and reject idempotency-key conflicts."""

    by_key: dict[str, Session14HumanReviewActionRecord] = {}
    for action in [*current, *incoming]:
        idempotency_key = action["idempotency_key"].strip()
        if not idempotency_key:
            raise ValueError("idempotency_key must not be blank")
        candidate = Session14HumanReviewActionRecord(
            action_id=action["action_id"],
            idempotency_key=idempotency_key,
            action=action["action"],
            actor=action["actor"],
            reason=action["reason"],
            revision=action["revision"],
            adjustments=[dict(item) for item in action["adjustments"]],
        )
        existing = by_key.get(idempotency_key)
        if existing is not None and existing != candidate:
            raise ValueError(f"conflicting idempotency_key: {idempotency_key}")
        by_key[idempotency_key] = candidate
    return sorted(
        by_key.values(),
        key=lambda action: (action["revision"], action["action_id"]),
    )


def merge_agent_contributions(
    current: list[AgentContribution],
    incoming: list[AgentContribution],
) -> list[AgentContribution]:
    """Merge identical replays once and reject conflicting identifier reuse."""

    by_id: dict[str, AgentContribution] = {}
    for contribution in [*current, *incoming]:
        contribution_id = contribution["contribution_id"].strip()
        if not contribution_id:
            raise ValueError("contribution_id must not be blank")
        candidate = AgentContribution(
            contribution_id=contribution_id,
            agent_id=contribution["agent_id"],
            sequence=contribution["sequence"],
            summary=contribution["summary"],
            state_delta_keys=list(contribution["state_delta_keys"]),
            action=contribution.get("action", "legacy_specialist_action"),
            tool_name=contribution.get("tool_name"),
            privilege_decision=contribution.get(
                "privilege_decision",
                "not_applicable",
            ),
            execution_status=contribution.get(
                "execution_status",
                "succeeded",
            ),
            validated_input_shape=dict(
                contribution.get("validated_input_shape", {})
            ),
            result_ref=contribution.get("result_ref"),
            duration_ms=contribution.get("duration_ms", 0),
        )
        existing = by_id.get(contribution_id)
        if existing is not None:
            existing_semantics = {
                key: value
                for key, value in existing.items()
                if key != "duration_ms"
            }
            candidate_semantics = {
                key: value
                for key, value in candidate.items()
                if key != "duration_ms"
            }
            if existing_semantics != candidate_semantics:
                raise ValueError(
                    f"conflicting contribution_id: {contribution_id}"
                )
            continue
        by_id[contribution_id] = candidate
    return sorted(
        by_id.values(),
        key=lambda contribution: (
            contribution["sequence"],
            contribution["contribution_id"],
        ),
    )


def merge_supervisor_route_events(
    current: list[SupervisorRouteEvent],
    incoming: list[SupervisorRouteEvent],
) -> list[SupervisorRouteEvent]:
    """Merge identical route replays and reject conflicting identifier reuse."""

    by_id: dict[str, SupervisorRouteEvent] = {}
    for route_event in [*current, *incoming]:
        route_event_id = route_event["route_event_id"].strip()
        if not route_event_id:
            raise ValueError("route_event_id must not be blank")
        candidate = SupervisorRouteEvent(
            route_event_id=route_event_id,
            sequence=route_event["sequence"],
            next_agent=route_event["next_agent"],
            reason_code=route_event["reason_code"],
            reason=route_event["reason"],
            route_source=route_event.get(
                "route_source",
                "deterministic_policy",
            ),
            proposed_agent=route_event.get("proposed_agent"),
            valid_candidates=list(route_event.get("valid_candidates", [])),
            fallback_reason=route_event.get(
                "fallback_reason",
                "proposer_unavailable",
            ),
        )
        existing = by_id.get(route_event_id)
        if existing is not None and existing != candidate:
            raise ValueError(f"conflicting route_event_id: {route_event_id}")
        by_id[route_event_id] = candidate
    return sorted(
        by_id.values(),
        key=lambda route_event: (
            route_event["sequence"],
            route_event["route_event_id"],
        ),
    )


class ReviewedEstimationGraphState(EstimationGraphState, total=False):
    """Reviewed V2/V3 fields layered on the mandatory graph contract."""

    human_review_mode: HumanReviewMode
    project_context: dict[str, object]
    reformulated_request: str
    pre_reformulation_transcript: str
    v2_profile: str
    v2_modules: list[dict[str, object]]
    structure_review_revision: int
    structure_review_status: StructureReviewStatus
    structure_review_record: StructureReviewRecord
    structure_route: StructureRoute
    recovery_status: RecoveryStatus
    recovery_route: RecoveryRoute
    recovery_runtime_result: dict[str, object]
    recovery_flagged_component_ids: list[str]
    recovery_recovered_component_ids: list[str]
    recovery_unresolved_component_ids: list[str]
    resolved_issue_codes: list[str]
    critic_report: dict[str, object]
    boss_decision: dict[str, object]
    boss_route: BossRoute
    active_provider: str
    provider_circuits: dict[str, dict[str, object]]
    execution_budgets: dict[str, object]
    parallel_retrieval_results: Annotated[
        list[dict[str, object]],
        merge_parallel_retrieval_results,
    ]
    final_review_revision: int
    final_review_status: str
    final_review_route: FinalReviewRoute
    final_review_record: dict[str, object]
    human_baseline_overrides: list[dict[str, object]]
    scenario_id: str
    parent_estimation_id: str
    parent_checkpoint_id: str
    semantic_assessment: dict[str, object]
    v3_complexity: dict[str, object]
    arbitrated_assessment: dict[str, object]
    v3_route_plan: dict[str, object]
    provider_selection: dict[str, object]
    stage_route_events: Annotated[list[dict[str, object]], operator.add]
    reliability_report: dict[str, object]
    proposal: dict[str, object]


class Session14EstimationGraphState(
    ReviewedEstimationGraphState,
    total=False,
):
    """Supervisor state layered additively on the reviewed V2/V3 contract."""

    requirements_extraction_completed: bool
    budget_search_completed: bool
    validation: dict[str, object] | None
    confidence: float | None
    thread_id: str
    historical_range_status: HistoricalRangeStatus
    human_review_revision: int
    human_review_status: Session14HumanReviewStatus
    human_review_reason_codes: list[Session14HumanReviewReasonCode]
    human_review_actions: Annotated[
        list[Session14HumanReviewActionRecord],
        merge_session14_human_review_actions,
    ]
    routing_steps: int
    max_routing_steps: int
    current_agent: Session14AgentId | None
    previous_agent: Session14AgentId | None
    next_agent: SupervisorDestination | None
    route_reason_code: RouteReasonCode | None
    route_events: Annotated[
        list[SupervisorRouteEvent],
        merge_supervisor_route_events,
    ]
    agent_contributions: Annotated[
        list[AgentContribution],
        merge_agent_contributions,
    ]


def new_session14_estimation_graph_state(
    *,
    transcript: str,
    estimation_id: str,
    graph_version: str = "session14.v1",
) -> Session14EstimationGraphState:
    """Build a fresh supervised state with independent accumulators."""

    state = Session14EstimationGraphState(
        **new_estimation_graph_state(
            transcript=transcript,
            estimation_id=estimation_id,
            graph_version=graph_version,
        )
    )
    state.update(
        {
            "requirements_extraction_completed": False,
            "budget_search_completed": False,
            "validation": None,
            "confidence": None,
            "thread_id": f"estimate:{estimation_id.strip()}",
            "historical_range_status": "unavailable",
            "human_review_revision": 1,
            "human_review_status": "not_requested",
            "human_review_reason_codes": [],
            "human_review_actions": [],
            "routing_steps": 0,
            "max_routing_steps": 12,
            "current_agent": None,
            "previous_agent": None,
            "next_agent": None,
            "route_reason_code": None,
            "route_events": [],
            "agent_contributions": [],
        }
    )
    return state
