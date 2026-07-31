"""Checkpoint-safe state for the additive Session 14 Plus graph."""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from app.generation.graph.review_state import (
    Session14EstimationGraphState,
    new_session14_estimation_graph_state,
)
from app.schemas.session14_plus_policy import ContextDetail


class Session14PlusCompactionEventPayload(TypedDict):
    event_id: str
    source_revision: int
    detail: ContextDetail
    context_id: str
    fingerprint: str
    retained_sections: list[str]
    dropped_item_counts: dict[str, int]


def merge_session14_plus_compaction_events(
    current: list[Session14PlusCompactionEventPayload],
    incoming: list[Session14PlusCompactionEventPayload],
) -> list[Session14PlusCompactionEventPayload]:
    """Deduplicate replayed compaction events and reject conflicting IDs."""

    by_id: dict[str, Session14PlusCompactionEventPayload] = {}
    for raw_event in [*current, *incoming]:
        event_id = raw_event["event_id"].strip()
        if not event_id:
            raise ValueError("event_id must not be blank")
        candidate = Session14PlusCompactionEventPayload(
            event_id=event_id,
            source_revision=raw_event["source_revision"],
            detail=raw_event["detail"],
            context_id=raw_event["context_id"],
            fingerprint=raw_event["fingerprint"],
            retained_sections=list(raw_event["retained_sections"]),
            dropped_item_counts=dict(raw_event["dropped_item_counts"]),
        )
        existing = by_id.get(event_id)
        if existing is not None and existing != candidate:
            raise ValueError(f"conflicting compaction event_id: {event_id}")
        by_id[event_id] = candidate
    return sorted(
        by_id.values(),
        key=lambda event: (event["source_revision"], event["event_id"]),
    )


class Session14PlusEstimationGraphState(
    Session14EstimationGraphState,
    total=False,
):
    """Session 14 state extended with provider and context integrity evidence."""

    plus_policy_version: str
    plus_execution_profile: Literal[
        "cost_first",
        "balanced",
        "quality_first",
        "human_controlled",
    ]
    plus_context_detail: ContextDetail
    plus_complexity_assessment: dict[str, object]
    plus_routing_plan: dict[str, object]
    plus_authorized_capabilities: dict[str, str]
    plus_context_source_revision: int
    plus_compacted_context: dict[str, object]
    plus_context_compaction_events: Annotated[
        list[Session14PlusCompactionEventPayload],
        merge_session14_plus_compaction_events,
    ]


def new_session14_plus_estimation_graph_state(
    *,
    transcript: str,
    estimation_id: str,
    graph_version: str = "session14.plus.v1",
    context_detail: ContextDetail = "medium",
) -> Session14PlusEstimationGraphState:
    """Build a fresh Plus state without sharing mutable accumulators."""

    state = Session14PlusEstimationGraphState(
        **new_session14_estimation_graph_state(
            transcript=transcript,
            estimation_id=estimation_id,
            graph_version=graph_version,
        )
    )
    state.update(
        plus_policy_version="session14-plus-policy-1.0.0",
        plus_execution_profile="balanced",
        plus_context_detail=context_detail,
        plus_complexity_assessment={},
        plus_routing_plan={},
        plus_authorized_capabilities={},
        plus_context_source_revision=0,
        plus_compacted_context={},
        plus_context_compaction_events=[],
    )
    return state
