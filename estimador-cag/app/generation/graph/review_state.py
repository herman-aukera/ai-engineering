"""Additional checkpoint-safe state used by the Session 13 Plus reviewed graph."""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from app.generation.graph.state import EstimationGraphState
from app.schemas.human_review import HumanReviewMode
from app.schemas.session14_supervision import (
    RouteReasonCode,
    SupervisorDestination,
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

class SupervisorRouteEvent(TypedDict):
    """One replay-safe, sanitized supervisor routing decision."""

    route_event_id: str
    sequence: int
    next_agent: SupervisorDestination
    reason_code: RouteReasonCode
    reason: str

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
        )
        existing = by_id.get(contribution_id)

        if existing is not None and existing != candidate:
            raise ValueError(
                f"conflicting contribution_id: {contribution_id}"
            )

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
        )
        existing = by_id.get(route_event_id)

        if existing is not None and existing != candidate:
            raise ValueError(
                f"conflicting route_event_id: {route_event_id}"
            )

        by_id[route_event_id] = candidate

    return sorted(
        by_id.values(),
        key=lambda route_event: (
            route_event["sequence"],
            route_event["route_event_id"],
        ),
    )


class ReviewedEstimationGraphState(EstimationGraphState, total=False):
    """Plus state fields layered on the frozen mandatory graph contract."""

    human_review_mode: HumanReviewMode
    project_context: dict[str, object]
    reformulated_request: str
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


class Session14EstimationGraphState(
    ReviewedEstimationGraphState,
    total=False,
):
    """Supervisor state layered additively on the Session 13 Plus contract."""

    requirements_extraction_completed: bool
    budget_search_completed: bool
    validation: dict[str, object] | None
    confidence: float | None
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
