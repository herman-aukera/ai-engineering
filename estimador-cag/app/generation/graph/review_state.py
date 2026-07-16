"""Additional checkpoint-safe state used by the Session 13 Plus reviewed graph."""

from __future__ import annotations

from typing import Literal, TypedDict

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


class StructureReviewRecord(TypedDict, total=False):
    action: str
    reason: str | None
    revision: int


class ReviewedEstimationGraphState(EstimationGraphState, total=False):
    """Plus state fields layered on the frozen mandatory graph contract."""

    human_review_mode: HumanReviewMode
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
    execution_budgets: dict[str, object]
