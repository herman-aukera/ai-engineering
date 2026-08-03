"""Replay-safe state for the consolidated Session 13 + 14 Plus graph."""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from app.generation.graph.session14_plus_state import (
    Session14PlusEstimationGraphState,
    new_session14_plus_estimation_graph_state,
)
from app.schemas.session14_plus_policy import ContextDetail

UnifiedDestination = Literal[
    "structure_phase",
    "estimation_phase",
    "candidate_competition",
    "reliability_analyst",
    "review_policy_phase",
    "boss_action",
    "recovery_phase",
    "coherence_validator",
    "human_review_gate",
    "proposal",
    "finalize",
]
UnifiedPhase = Literal[
    "bootstrap",
    "structure",
    "estimation",
    "competition",
    "reliability",
    "review_policy",
    "recovery",
    "coherence",
    "human_review",
    "proposal",
    "finalized",
]


class UnifiedRouteEvent(TypedDict):
    """One deterministic supervisor decision with replay-safe identity."""

    event_id: str
    sequence: int
    destination: UnifiedDestination
    reason_code: str
    summary: str


def merge_unified_route_events(
    current: list[UnifiedRouteEvent],
    incoming: list[UnifiedRouteEvent],
) -> list[UnifiedRouteEvent]:
    """Deduplicate identical replay and reject conflicting route identifiers."""

    by_id: dict[str, UnifiedRouteEvent] = {}
    for raw_event in [*current, *incoming]:
        event_id = raw_event["event_id"].strip()
        if not event_id:
            raise ValueError("unified route event_id must not be blank")
        candidate = UnifiedRouteEvent(
            event_id=event_id,
            sequence=raw_event["sequence"],
            destination=raw_event["destination"],
            reason_code=raw_event["reason_code"].strip(),
            summary=raw_event["summary"].strip(),
        )
        existing = by_id.get(event_id)
        if existing is not None and existing != candidate:
            raise ValueError(f"conflicting unified route event_id: {event_id}")
        by_id[event_id] = candidate
    return sorted(
        by_id.values(),
        key=lambda event: (event["sequence"], event["event_id"]),
    )


class UnifiedEstimationGraphState(
    Session14PlusEstimationGraphState,
    total=False,
):
    """Superset state that keeps reviewed evidence under one supervisor."""

    unified_graph_version: str
    unified_policy_version: str
    unified_phase: UnifiedPhase
    unified_review_authority: str
    unified_structure_completed: bool
    unified_estimation_completed: bool
    unified_reliability_completed: bool
    unified_review_policy_completed: bool
    unified_boss_action_completed: bool
    unified_recovery_cycles: int
    unified_max_recovery_cycles: int
    unified_coherence_completed: bool
    unified_proposal_completed: bool
    unified_route_events: Annotated[
        list[UnifiedRouteEvent],
        merge_unified_route_events,
    ]


def new_unified_estimation_graph_state(
    *,
    transcript: str,
    estimation_id: str,
    graph_version: str = "session13_14_plus.unified.v1",
    context_detail: ContextDetail = "medium",
) -> UnifiedEstimationGraphState:
    """Build a fresh unified state without sharing mutable accumulators."""

    state = UnifiedEstimationGraphState(
        **new_session14_plus_estimation_graph_state(
            transcript=transcript,
            estimation_id=estimation_id,
            graph_version=graph_version,
            context_detail=context_detail,
        )
    )
    state.update(
        unified_graph_version=graph_version,
        unified_policy_version="session13_14_plus.unified-policy.v1",
        unified_phase="bootstrap",
        unified_review_authority=(
            "deterministic_supervisor_routes; critics_recommend; human_gate_authorizes"
        ),
        unified_structure_completed=False,
        unified_estimation_completed=False,
        unified_reliability_completed=False,
        unified_review_policy_completed=False,
        unified_boss_action_completed=False,
        unified_recovery_cycles=0,
        unified_max_recovery_cycles=2,
        unified_coherence_completed=False,
        unified_proposal_completed=False,
        unified_route_events=[],
    )
    return state
