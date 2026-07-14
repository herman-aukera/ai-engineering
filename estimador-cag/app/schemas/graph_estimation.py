"""Public HTTP contracts for the additive Session 13 graph endpoint."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


class GraphEstimationRequest(StrictPayload):
    """Transcript and optional stable identifier for one graph thread."""

    transcript: str = Field(min_length=10, max_length=50_000)
    estimation_id: UUID | None = None


class GraphEstimationResponse(StrictPayload):
    """Terminal graph state without the original transcript."""

    estimation_id: UUID
    thread_id: str = Field(min_length=1, max_length=128)
    graph_version: str = Field(min_length=1)
    status: Literal["validated", "needs_review"]
    review_required: bool
    estimate: GraphEstimatePayload
    requirements: list[RequirementPayload]
    components: list[ComponentPayload]
    budget_matches: list[BudgetMatchPayload]
    component_estimates: list[ComponentEstimatePayload]
    errors: list[GraphIssuePayload]
    trace_events: list[DomainTraceEventPayload]
    provider_metadata: ProviderMetadataPayload
    execution_metadata: ExecutionMetadataPayload
