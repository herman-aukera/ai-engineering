"""
Typed shared state and checkpoint-safe contracts for the Session 13 graph.

The graph state contains data only. Runtime services, model clients, database
sessions, open connections, and other non-serializable objects must be injected
into nodes rather than stored here.
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

GraphStatus = Literal["pending", "validated", "needs_review"]
GroundingStatus = Literal[
    "grounded",
    "low_confidence",
    "conflict",
    "no_data",
]
IssueSeverity = Literal["warning", "error"]


class RequirementItem(TypedDict):
    """One atomic requirement extracted from the transcript."""

    requirement_id: str
    text: str


class ComponentItem(TypedDict):
    """One stable implementation component classified from requirements."""

    component_id: str
    name: str
    category: str
    requirement_ids: list[str]


class BudgetMatch(TypedDict):
    """One retrieved reference retained with estimation provenance."""

    component_id: str
    budget_id: str
    reference_component_id: str | None
    source_document_id: str
    source_chunk_id: str
    recorded_hours: float | None
    distance: float | None
    score: float | None
    retrieval_method: str


class ComponentEstimate(TypedDict):
    """One deterministic component estimate derived from reference evidence."""

    component_id: str
    name: str
    hours: float | None
    grounding_status: GroundingStatus
    reference_budget_ids: list[str]
    reference_component_ids: list[str]
    source_hours: list[float]
    source_range_low: float | None
    source_range_high: float | None
    dispersion: float | None
    confidence: float
    derivation_method: str
    review_reasons: list[str]


class GraphEstimate(TypedDict):
    """Internal deterministic estimate before HTTP response adaptation."""

    components: list[ComponentEstimate]
    subtotal_hours: float | None
    contingency_hours: float | None
    total_hours: float | None
    total_cost_eur: float | None
    currency: str


class GraphIssue(TypedDict):
    """A structured graph issue safe for checkpointing and diagnostics."""

    code: str
    message: str
    node: str
    severity: IssueSeverity


class DomainTraceEvent(TypedDict):
    """One concise domain event, distinct from logs and telemetry spans."""

    event_type: str
    node: str
    summary: str
    evidence_refs: list[str]
    state_delta_keys: list[str]


class ProviderMetadata(TypedDict, total=False):
    """Sanitized provider metadata without prompts, keys, or raw responses."""

    provider: str
    model: str
    prompt_version: str


class ExecutionMetadata(TypedDict, total=False):
    """Small JSON-safe execution diagnostics."""

    requirement_count: int
    component_count: int
    budget_match_count: int
    graph_version: str


class EstimationGraphState(TypedDict, total=False):
    """Partial shared state used by the five required Session 13 nodes."""

    transcript: str
    estimation_id: str
    graph_version: str

    requirements: list[RequirementItem]
    components: list[ComponentItem]

    budget_matches: Annotated[list[BudgetMatch], operator.add]
    component_estimates: list[ComponentEstimate]

    estimate: GraphEstimate
    status: GraphStatus
    review_required: bool

    errors: Annotated[list[GraphIssue], operator.add]
    trace_events: Annotated[list[DomainTraceEvent], operator.add]

    provider_metadata: ProviderMetadata
    execution_metadata: ExecutionMetadata


def new_estimation_graph_state(
    *,
    transcript: str,
    estimation_id: str,
    graph_version: str = "session13.v1",
) -> EstimationGraphState:
    """Build a fresh graph state with independent mutable accumulators."""

    if not transcript.strip():
        raise ValueError("transcript must not be blank")

    normalized_estimation_id = estimation_id.strip()
    if not normalized_estimation_id:
        raise ValueError("estimation_id must not be blank")

    normalized_graph_version = graph_version.strip()
    if not normalized_graph_version:
        raise ValueError("graph_version must not be blank")

    return EstimationGraphState(
        transcript=transcript,
        estimation_id=normalized_estimation_id,
        graph_version=normalized_graph_version,
        requirements=[],
        components=[],
        budget_matches=[],
        component_estimates=[],
        status="pending",
        review_required=False,
        errors=[],
        trace_events=[],
        provider_metadata={},
        execution_metadata={},
    )
