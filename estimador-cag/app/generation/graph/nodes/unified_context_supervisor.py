"""Context-integrity wrapper for the canonical unified supervisor."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy

from langgraph.types import Command

from app.generation.graph.nodes.session14_plus_policy import (
    build_session14_plus_context_source,
)
from app.generation.graph.nodes.unified_supervisor import (
    build_unified_supervisor_node,
)
from app.generation.graph.unified_state import UnifiedEstimationGraphState
from app.schemas.session14_plus_policy import ContextDetail
from app.services.session14_plus_policy import (
    build_context_compaction_event,
    compact_session14_context,
)

_ACCUMULATOR_KEYS = (
    "route_events",
    "agent_contributions",
    "human_review_actions",
    "unified_route_events",
)


def _project_update(
    state: Mapping[str, object],
    update: Mapping[str, object],
) -> dict[str, object]:
    """Project reducer-backed deltas without mutating authoritative state."""

    projected = deepcopy(dict(state))
    projected.update(deepcopy(dict(update)))
    for key in _ACCUMULATOR_KEYS:
        current_items = state.get(key)
        incoming_items = update.get(key)
        if isinstance(current_items, list) and isinstance(incoming_items, list):
            projected[key] = [
                *deepcopy(current_items),
                *deepcopy(incoming_items),
            ]
    return projected


def _unified_route_decisions(
    state: Mapping[str, object],
) -> list[str]:
    decisions: list[str] = []
    raw_events = state.get("unified_route_events")
    if not isinstance(raw_events, list):
        return decisions
    for raw_event in raw_events:
        if not isinstance(raw_event, Mapping):
            continue
        destination = raw_event.get("destination")
        reason_code = raw_event.get("reason_code")
        if isinstance(destination, str) and isinstance(reason_code, str):
            decisions.append(
                f"unified-route:{reason_code}->{destination}"
            )
    return decisions


def build_context_aware_unified_supervisor_node(
    *,
    context_detail: ContextDetail,
    repository_state: Mapping[str, str],
):
    """Refresh a sanitized context projection after every route decision."""

    base_supervisor = build_unified_supervisor_node()

    async def context_aware_supervisor(
        state: UnifiedEstimationGraphState,
    ) -> Command:
        command = await base_supervisor(state)
        raw_update = command.update or {}
        if not isinstance(raw_update, Mapping):
            raise ValueError("unified supervisor update must be a mapping")

        projected = _project_update(state, raw_update)
        source_revision = int(
            state.get("plus_context_source_revision", 0)
        ) + 1
        source = build_session14_plus_context_source(
            projected,
            source_revision=source_revision,
            repository_state=repository_state,
        )
        accepted = list(source.accepted_decisions)
        for decision in _unified_route_decisions(projected):
            if decision not in accepted:
                accepted.append(decision)
        source = source.model_copy(
            update={"accepted_decisions": accepted}
        )
        context = compact_session14_context(
            source,
            detail=context_detail,
        )
        event = build_context_compaction_event(
            context,
            event_id=(
                f"{source.identity['estimation_id']}:context:"
                f"{source_revision}"
            ),
        )
        return Command(
            goto=command.goto,
            update={
                **dict(raw_update),
                "plus_context_source_revision": source_revision,
                "plus_compacted_context": context.model_dump(mode="json"),
                "plus_context_compaction_events": [
                    event.model_dump(mode="json")
                ],
            },
        )

    return context_aware_supervisor
