"""Public API contracts for durable reviewed graph executions."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.human_review import (
    FinalEstimateReviewDecision,
    HumanReviewMode,
    StructureReviewDecision,
)


class StrictReviewedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReviewedGraphStartRequest(StrictReviewedPayload):
    transcript: str = Field(min_length=20, max_length=50_000)
    human_review_mode: HumanReviewMode = "risk_based"
    estimation_id: UUID | None = None


class ReviewedGraphResumeRequest(StructureReviewDecision):
    """Validated structure decision used as the LangGraph resume value."""


class ReviewedGraphFinalResumeRequest(FinalEstimateReviewDecision):
    """Validated final-estimate decision used as the resume value."""


class ReviewedInterruptPayload(StrictReviewedPayload):
    id: str | None = None
    value: Any


class ReviewedGraphExecutionResponse(StrictReviewedPayload):
    execution_status: Literal["paused", "completed"]
    estimation_id: UUID
    thread_id: str = Field(min_length=1, max_length=128)
    graph_version: str = Field(min_length=1)
    graph_status: Literal["pending", "validated", "needs_review"]
    review_required: bool
    human_review_mode: HumanReviewMode
    structure_review_revision: int = Field(ge=0)
    structure_review_status: str | None = None
    final_review_revision: int = Field(ge=0)
    final_review_status: str | None = None
    next_nodes: list[str]
    interrupts: list[ReviewedInterruptPayload]
    state: dict[str, Any]


class ReviewedCheckpointResponse(StrictReviewedPayload):
    checkpoint_id: str = Field(min_length=1)
    created_at: str | None = None
    next_nodes: list[str]
    state: dict[str, Any]


class ReviewedCheckpointHistoryResponse(StrictReviewedPayload):
    estimation_id: UUID
    checkpoints: list[ReviewedCheckpointResponse]


class ReviewedScenarioBranchRequest(StrictReviewedPayload):
    checkpoint_id: str = Field(min_length=1, max_length=240)
    scenario_id: str = Field(min_length=1, max_length=120)


class ReviewedScenarioComparisonRequest(StrictReviewedPayload):
    left_estimation_id: UUID
    right_estimation_id: UUID


class ReviewedScenarioComparisonResponse(StrictReviewedPayload):
    left_estimation_id: UUID
    right_estimation_id: UUID
    comparison: dict[str, Any]


class ReviewedAuditPacketResponse(StrictReviewedPayload):
    packet: dict[str, Any]
