"""Additional checkpoint-safe state used by the Session 13 Plus reviewed graph."""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from app.generation.graph.state import EstimationGraphState
from app.schemas.human_review import HumanReviewMode

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
    parallel_retrieval_results: Annotated[list[dict[str, object]], merge_parallel_retrieval_results]
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
