"""Deterministic evidence classification and routing nodes."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from app.energy_chat.contracts import (
    ProjectRagRequest,
    ProjectRagResult,
    SourceNeedRequest,
    SourceNeedResult,
)
from app.energy_chat.graph_state import (
    EnergyChatGraphState,
    GraphStateRecord,
    TraceEvent,
    append_unique_records,
    append_unique_values,
    build_trace_event,
    validated_state_update,
)
from app.energy_chat.rag import retrieve_project_context
from app.energy_chat.source_guard import classify_source_need

EvidenceRoute = Literal["skip", "retrieve_project", "external_required"]


class EvidenceNeedDelta(GraphStateRecord):
    """Typed output of deterministic evidence-need classification."""

    source_need: SourceNeedResult
    status: Literal["evidence_classified"] = "evidence_classified"
    trace_events: list[TraceEvent] = Field(min_length=1, max_length=1)


class EvidenceRoutingDelta(GraphStateRecord):
    """Typed result of skip, project retrieval, or external-evidence routing."""

    route: EvidenceRoute
    evidence_refs: list[str] = Field(default_factory=list)
    project_rag: ProjectRagResult | None = None
    status: Literal["evidence_ready", "awaiting_evidence"]
    trace_events: list[TraceEvent] = Field(min_length=1, max_length=1)

    @model_validator(mode="after")
    def route_matches_payload(self) -> EvidenceRoutingDelta:
        if self.route == "retrieve_project" and self.project_rag is None:
            raise ValueError("retrieve_project requires a project_rag result")
        if self.route != "retrieve_project" and self.project_rag is not None:
            raise ValueError("Only retrieve_project may write project_rag")
        if self.route == "external_required" and self.status != "awaiting_evidence":
            raise ValueError("external_required must await evidence")
        if self.route != "external_required" and self.status != "evidence_ready":
            raise ValueError("completed evidence routes must be evidence_ready")
        return self


def determine_evidence_need(state: EnergyChatGraphState) -> EvidenceNeedDelta:
    """Classify source need using the existing authoritative deterministic classifier."""

    result = classify_source_need(
        SourceNeedRequest(
            user_message=state.user_request,
            mode=state.mode,
            evidence_refs=state.evidence_refs,
        )
    )
    event = build_trace_event(
        state,
        event_type="evidence_need_classified",
        event_key=f"evidence_need_classified:{result.decision}",
        producer="determine_evidence_need",
        payload={
            "decision": result.decision,
            "detected_marker_count": len(result.detected_markers),
            "requires_current_sources": result.requires_current_sources,
            "requires_project_sources": result.requires_project_sources,
        },
    )
    return EvidenceNeedDelta(source_need=result, trace_events=[event])


def route_evidence(state: EnergyChatGraphState, *, k: int = 3) -> EvidenceRoutingDelta:
    """Route classified requests without treating project sources as current evidence."""

    if state.source_need is None:
        raise ValueError("Evidence need must be classified before routing")

    route = select_evidence_route(state.source_need)
    if route == "external_required":
        rag = None
        refs: list[str] = []
        status = "awaiting_evidence"
    elif route == "retrieve_project":
        rag = retrieve_project_context(
            ProjectRagRequest(query=state.user_request, mode=state.mode, k=k)
        )
        refs = rag.evidence_refs
        status = "evidence_ready"
    else:
        route = "skip"
        rag = None
        refs = []
        status = "evidence_ready"

    event = build_trace_event(
        state,
        event_type="evidence_routed",
        event_key=f"evidence_routed:{route}",
        producer="route_evidence",
        payload={
            "evidence_ref_count": len(refs),
            "route": route,
        },
    )
    return EvidenceRoutingDelta(
        route=route,
        evidence_refs=refs,
        project_rag=rag,
        status=status,
        trace_events=[event],
    )


def select_evidence_route(source_need: SourceNeedResult) -> EvidenceRoute:
    """Choose the deterministic evidence branch without performing retrieval."""

    if source_need.missing_evidence and source_need.requires_current_sources:
        return "external_required"
    if source_need.missing_evidence and source_need.requires_project_sources:
        return "retrieve_project"
    return "skip"


def apply_evidence_need_delta(
    state: EnergyChatGraphState, delta: EvidenceNeedDelta
) -> EnergyChatGraphState:
    """Apply source classification and its append-only trace event."""

    return validated_state_update(
        state,
        source_need=delta.source_need,
        status=delta.status,
        trace_events=append_unique_records(
            state.trace_events, delta.trace_events, id_field="event_id"
        ),
    )


def apply_evidence_routing_delta(
    state: EnergyChatGraphState, delta: EvidenceRoutingDelta
) -> EnergyChatGraphState:
    """Apply routed evidence without replacing previously attributed references."""

    return validated_state_update(
        state,
        evidence_refs=append_unique_values(state.evidence_refs, delta.evidence_refs),
        project_rag=delta.project_rag if delta.project_rag is not None else state.project_rag,
        status=delta.status,
        trace_events=append_unique_records(
            state.trace_events, delta.trace_events, id_field="event_id"
        ),
    )
