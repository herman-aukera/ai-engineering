"""Context-integrity wrapper for the Session 14 Plus human gate."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from copy import deepcopy
from typing import Literal

from langgraph.types import Command

from app.generation.graph.nodes.session14_plus_policy import (
    build_session14_plus_context_source,
)
from app.generation.graph.session14_plus_state import (
    Session14PlusEstimationGraphState,
)
from app.schemas.session14_plus_policy import ContextDetail
from app.services.session14_plus_policy import (
    build_context_compaction_event,
    compact_session14_context,
)

Session14PlusHumanReviewGate = Callable[
    [Session14PlusEstimationGraphState],
    Awaitable[Command[Literal["finalize"]]],
]


def build_context_aware_session14_plus_human_gate(
    base_gate: Session14PlusHumanReviewGate,
    *,
    default_context_detail: ContextDetail,
    repository_state: Mapping[str, str],
) -> Session14PlusHumanReviewGate:
    """Refresh compacted context after an authorized resume decision."""

    async def context_aware_gate(
        state: Session14PlusEstimationGraphState,
    ) -> Command[Literal["finalize"]]:
        command = await base_gate(state)
        raw_update = command.update or {}
        if not isinstance(raw_update, Mapping):
            raise ValueError("human review update must be a mapping")

        projected = deepcopy(dict(state))
        projected.update(deepcopy(dict(raw_update)))
        current_actions = state.get("human_review_actions")
        incoming_actions = raw_update.get("human_review_actions")
        if isinstance(current_actions, list) and isinstance(
            incoming_actions,
            list,
        ):
            projected["human_review_actions"] = [
                *deepcopy(current_actions),
                *deepcopy(incoming_actions),
            ]

        source_revision = int(
            state.get("plus_context_source_revision", 0)
        ) + 1
        raw_detail = state.get(
            "plus_context_detail",
            default_context_detail,
        )
        detail: ContextDetail = (
            raw_detail
            if raw_detail in {"minimal", "medium", "max"}
            else default_context_detail
        )
        source = build_session14_plus_context_source(
            projected,
            source_revision=source_revision,
            repository_state=repository_state,
        )
        context = compact_session14_context(source, detail=detail)
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
                "plus_compacted_context": context.model_dump(
                    mode="json"
                ),
                "plus_context_compaction_events": [
                    event.model_dump(mode="json")
                ],
            },
        )

    return context_aware_gate
