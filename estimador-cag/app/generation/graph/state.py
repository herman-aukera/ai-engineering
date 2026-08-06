"""
Typed shared state and checkpoint-safe contracts for the Session 13 graph.

The graph state contains data only. Runtime services, model clients, database
sessions, open connections, and other non-serializable objects must be injected
into nodes rather than stored here.
"""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal, NotRequired, TypedDict

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

    match_id: NotRequired[str]
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

    issue_id: NotRequired[str]
    code: str
    message: str
    node: str
    severity: IssueSeverity


class DomainTraceEvent(TypedDict):
    """One concise domain event, distinct from logs and telemetry spans."""

    event_id: NotRequired[str]
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
    component_estimate_count: int
    graph_version: str


def _stable_record_id(prefix: str, payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()[:24]
    return f"{prefix}:{digest}"


def _optional_record_id(raw_value: object, *, field_name: str) -> str | None:
    if raw_value is None:
        return None
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ValueError(f"{field_name} must be a non-blank string")
    return raw_value.strip()


def _budget_match_identity(match: BudgetMatch) -> str:
    explicit = _optional_record_id(match.get("match_id"), field_name="match_id")
    if explicit is not None:
        return explicit
    return _stable_record_id(
        "budget-match",
        {
            "component_id": match["component_id"],
            "budget_id": match["budget_id"],
            "reference_component_id": match["reference_component_id"],
            "source_document_id": match["source_document_id"],
            "source_chunk_id": match["source_chunk_id"],
            "retrieval_method": match["retrieval_method"],
        },
    )


def merge_budget_matches(
    current: list[BudgetMatch],
    incoming: list[BudgetMatch],
) -> list[BudgetMatch]:
    """Deduplicate replayed evidence and reject semantic identity conflicts."""

    by_id: dict[str, BudgetMatch] = {}
    for raw_match in [*current, *incoming]:
        candidate = BudgetMatch(**dict(raw_match))
        record_id = _budget_match_identity(candidate)
        existing = by_id.get(record_id)
        if existing is not None and existing != candidate:
            raise ValueError(f"conflicting budget match identity: {record_id}")
        by_id[record_id] = candidate
    return [by_id[record_id] for record_id in sorted(by_id)]


def _graph_issue_identity(issue: GraphIssue) -> str:
    explicit = _optional_record_id(issue.get("issue_id"), field_name="issue_id")
    if explicit is not None:
        return explicit
    return _stable_record_id(
        "graph-issue",
        {"code": issue["code"], "node": issue["node"]},
    )


def merge_graph_issues(
    current: list[GraphIssue],
    incoming: list[GraphIssue],
) -> list[GraphIssue]:
    """Deduplicate identical issue replay and fail closed on conflicting reuse."""

    by_id: dict[str, GraphIssue] = {}
    for raw_issue in [*current, *incoming]:
        candidate = GraphIssue(**dict(raw_issue))
        record_id = _graph_issue_identity(candidate)
        existing = by_id.get(record_id)
        if existing is not None and existing != candidate:
            raise ValueError(f"conflicting graph issue identity: {record_id}")
        by_id[record_id] = candidate
    return [by_id[record_id] for record_id in sorted(by_id)]


def _trace_event_identity(event: DomainTraceEvent) -> str:
    explicit = _optional_record_id(event.get("event_id"), field_name="event_id")
    if explicit is not None:
        return explicit
    return _stable_record_id(
        "trace-event",
        {
            "event_type": event["event_type"],
            "node": event["node"],
            "evidence_refs": sorted(event["evidence_refs"]),
            "state_delta_keys": sorted(event["state_delta_keys"]),
        },
    )


def merge_trace_events(
    current: list[DomainTraceEvent],
    incoming: list[DomainTraceEvent],
) -> list[DomainTraceEvent]:
    """Deduplicate replayed trace deltas with deterministic semantic ordering."""

    by_id: dict[str, DomainTraceEvent] = {}
    for raw_event in [*current, *incoming]:
        candidate = DomainTraceEvent(
            **{
                **dict(raw_event),
                "evidence_refs": list(raw_event["evidence_refs"]),
                "state_delta_keys": list(raw_event["state_delta_keys"]),
            }
        )
        record_id = _trace_event_identity(candidate)
        existing = by_id.get(record_id)
        if existing is not None and existing != candidate:
            raise ValueError(f"conflicting trace event identity: {record_id}")
        by_id[record_id] = candidate
    return [by_id[record_id] for record_id in sorted(by_id)]


class EstimationGraphState(TypedDict, total=False):
    """Partial shared state used by the five required Session 13 nodes."""

    transcript: str
    estimation_id: str
    graph_version: str

    requirements: list[RequirementItem]
    components: list[ComponentItem]

    budget_matches: Annotated[list[BudgetMatch], merge_budget_matches]
    component_estimates: list[ComponentEstimate]

    estimate: GraphEstimate
    status: GraphStatus
    review_required: bool

    errors: Annotated[list[GraphIssue], merge_graph_issues]
    trace_events: Annotated[list[DomainTraceEvent], merge_trace_events]

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
