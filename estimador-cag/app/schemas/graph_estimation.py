"""Public HTTP contracts for the additive Session 13 graph endpoint."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.session14_human_review import (
    HistoricalRangeStatus,
    Session14HumanReviewDecision,
    Session14HumanReviewReasonCode,
    Session14HumanReviewStatus,
)


class StrictPayload(BaseModel):
    """Reject undeclared HTTP fields at every public contract boundary."""

    model_config = ConfigDict(extra="forbid")


class RequirementPayload(StrictPayload):
    requirement_id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class ComponentPayload(StrictPayload):
    component_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    requirement_ids: list[str]


class BudgetMatchPayload(StrictPayload):
    component_id: str = Field(min_length=1)
    budget_id: str = Field(min_length=1)
    reference_component_id: str | None = None
    source_document_id: str = Field(min_length=1)
    source_chunk_id: str = Field(min_length=1)
    recorded_hours: float | None = Field(default=None, gt=0)
    distance: float | None = Field(default=None, ge=0)
    score: float | None = None
    retrieval_method: str = Field(min_length=1)


class ComponentEstimatePayload(StrictPayload):
    component_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    hours: float | None = Field(default=None, gt=0)
    grounding_status: Literal[
        "grounded",
        "low_confidence",
        "conflict",
        "no_data",
    ]
    reference_budget_ids: list[str]
    reference_component_ids: list[str]
    source_hours: list[float]
    source_range_low: float | None = Field(default=None, gt=0)
    source_range_high: float | None = Field(default=None, gt=0)
    dispersion: float | None = Field(default=None, ge=0)
    confidence: float = Field(ge=0, le=1)
    derivation_method: str = Field(min_length=1)
    review_reasons: list[str]


class GraphEstimatePayload(StrictPayload):
    components: list[ComponentEstimatePayload]
    subtotal_hours: float | None = Field(default=None, ge=0)
    contingency_hours: float | None = Field(default=None, ge=0)
    total_hours: float | None = Field(default=None, ge=0)
    total_cost_eur: float | None = Field(default=None, ge=0)
    currency: Literal["EUR"]


class GraphIssuePayload(StrictPayload):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    node: str = Field(min_length=1)
    severity: Literal["warning", "error"]


class DomainTraceEventPayload(StrictPayload):
    event_type: str = Field(min_length=1)
    node: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    evidence_refs: list[str]
    state_delta_keys: list[str]


class ProviderMetadataPayload(StrictPayload):
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None


class ExecutionMetadataPayload(StrictPayload):
    requirement_count: int | None = Field(default=None, ge=0)
    component_count: int | None = Field(default=None, ge=0)
    budget_match_count: int | None = Field(default=None, ge=0)
    component_estimate_count: int | None = Field(
        default=None,
        ge=0,
    )
    graph_version: str | None = None


class SupervisorRouteEventPayload(StrictPayload):
    route_event_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    next_agent: str = Field(min_length=1)
    reason_code: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class AgentContributionPayload(StrictPayload):
    contribution_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    summary: str = Field(min_length=1)
    state_delta_keys: list[str]


class Session14EstimateSummaryPayload(StrictPayload):
    total_hours: float | None = Field(default=None, ge=0)
    component_count: int = Field(ge=0)


class Session14InterruptValuePayload(StrictPayload):
    gate: Literal["session14_human_review"]
    estimation_id: UUID
    thread_id: str = Field(min_length=1, max_length=128)
    revision: int = Field(ge=1)
    reason_codes: list[str]
    estimate_summary: Session14EstimateSummaryPayload
    confidence: float | None = Field(default=None, ge=0, le=1)
    historical_range_status: HistoricalRangeStatus
    evidence_count: int = Field(ge=0)
    active_findings: list[str]
    allowed_actions: list[Literal["approve", "adjust", "reject"]]


class Session14InterruptPayload(StrictPayload):
    id: str | None = None
    value: Session14InterruptValuePayload


class GraphEstimationRequest(StrictPayload):
    """Transcript and optional stable identifier for one graph thread."""

    transcript: str = Field(min_length=10, max_length=50_000)
    estimation_id: UUID | None = None


class GraphHumanReviewResumeRequest(Session14HumanReviewDecision):
    """Strict Task 14 resume value accepted by the public endpoint."""


class GraphEstimationResponse(StrictPayload):
    """Terminal graph state without the original transcript."""

    estimation_id: UUID
    thread_id: str = Field(min_length=1, max_length=128)
    graph_version: str = Field(min_length=1)
    status: Literal[
        "validated",
        "needs_review",
        "awaiting_human_review",
    ]
    review_required: bool
    estimate: GraphEstimatePayload
    requirements: list[RequirementPayload]
    components: list[ComponentPayload]
    budget_matches: list[BudgetMatchPayload]
    component_estimates: list[ComponentEstimatePayload]
    errors: list[GraphIssuePayload]
    trace_events: list[DomainTraceEventPayload]
    route_events: list[SupervisorRouteEventPayload] = Field(
        default_factory=list
    )
    agent_contributions: list[AgentContributionPayload] = Field(
        default_factory=list
    )
    revision: int = Field(default=0, ge=0)
    human_review_status: Session14HumanReviewStatus | None = None
    human_review_reason_codes: list[
        Session14HumanReviewReasonCode
    ] = Field(
        default_factory=list
    )
    human_review: Session14InterruptPayload | None = None
    provider_metadata: ProviderMetadataPayload
    execution_metadata: ExecutionMetadataPayload
