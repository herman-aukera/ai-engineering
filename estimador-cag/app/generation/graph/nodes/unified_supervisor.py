"""Single deterministic supervisor for the consolidated Plus graph."""

from __future__ import annotations

from collections.abc import Mapping

from langgraph.types import Command

from app.generation.graph.unified_state import (
    UnifiedDestination,
    UnifiedEstimationGraphState,
    UnifiedPhase,
    UnifiedRouteEvent,
)

_POLICY_VERSION = "session13_14_plus.unified-supervisor.v1"

_PHASE_BY_DESTINATION: dict[UnifiedDestination, UnifiedPhase] = {
    "structure_phase": "structure",
    "estimation_phase": "estimation",
    "candidate_competition": "competition",
    "reliability_analyst": "reliability",
    "review_policy_phase": "review_policy",
    "boss_action": "review_policy",
    "recovery_phase": "recovery",
    "coherence_validator": "coherence",
    "human_review_gate": "human_review",
    "proposal": "proposal",
    "finalize": "finalized",
}


def _positive_int(value: object, *, default: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return default
    return value


def _has_mapping(state: Mapping[str, object], key: str) -> bool:
    value = state.get(key)
    return isinstance(value, Mapping) and bool(value)


def _route(
    state: UnifiedEstimationGraphState,
) -> tuple[UnifiedDestination, str, str, bool]:
    """Return destination, reason code, summary, and forced-review flag."""

    if not state.get("unified_structure_completed", False):
        return (
            "structure_phase",
            "structure_not_completed",
            "Run reformulation, semantic classification, extraction, classification, and structure review.",
            False,
        )

    if state.get("structure_route") == "stop":
        return (
            "finalize",
            "structure_review_stopped",
            "A persisted structure-review decision stopped the execution.",
            False,
        )

    if not state.get("unified_estimation_completed", False):
        return (
            "estimation_phase",
            "estimation_not_completed",
            "Run bounded retrieval, deterministic estimation, validation, and selective recovery.",
            False,
        )

    if not state.get("plus_competition_completed", False):
        return (
            "candidate_competition",
            "competition_not_completed",
            "Create baseline, aggressive, conservative, and synthesized candidates under Python policy.",
            False,
        )

    if not state.get("unified_reliability_completed", False):
        return (
            "reliability_analyst",
            "reliability_not_completed",
            "Produce a reliability assessment before policy review.",
            False,
        )

    if not state.get("unified_review_policy_completed", False):
        return (
            "review_policy_phase",
            "critic_policy_not_completed",
            "Run the typed deterministic Critic and bounded Boss recommendation.",
            False,
        )

    if not state.get("unified_boss_action_completed", False):
        return (
            "boss_action",
            "boss_recommendation_not_applied",
            "Translate the Boss recommendation into bounded budgets and a supervisor-visible route.",
            False,
        )

    boss_route = state.get("boss_route", "final_review")
    if boss_route == "recover":
        cycles = _positive_int(state.get("unified_recovery_cycles"), default=0)
        maximum = _positive_int(
            state.get("unified_max_recovery_cycles"),
            default=2,
        )
        if cycles < maximum:
            return (
                "recovery_phase",
                "bounded_recovery_requested",
                f"Run selective recovery cycle {cycles + 1} of {maximum}.",
                False,
            )
        return (
            "coherence_validator",
            "recovery_budget_exhausted",
            "Recovery budget is exhausted; validate the retained candidate and require human authority.",
            True,
        )

    if not state.get("unified_coherence_completed", False):
        return (
            "coherence_validator",
            "coherence_not_completed",
            "Run the independent deterministic coherence validator after competition and policy review.",
            boss_route == "stop",
        )

    status = str(state.get("status", "pending"))
    review_required = bool(state.get("review_required", False))
    if (
        review_required
        or status != "validated"
        or boss_route == "stop"
        or not _has_mapping(state, "validation")
    ):
        return (
            "human_review_gate",
            "human_authority_required",
            "Pause or resolve the final decision through the persisted Session 14 human gate.",
            True,
        )

    if not state.get("unified_proposal_completed", False):
        return (
            "proposal",
            "proposal_not_completed",
            "Project the validated estimate into the reviewed proposal contract.",
            False,
        )

    return (
        "finalize",
        "unified_workflow_completed",
        "All unified phases and policy gates completed.",
        False,
    )


def _next_sequence(state: UnifiedEstimationGraphState) -> int:
    """Synchronize replay-safe route history with the legacy routing counter."""

    legacy_sequence = _positive_int(state.get("routing_steps"), default=0)
    event_sequence = max(
        (
            _positive_int(event.get("sequence"), default=0)
            for event in state.get("unified_route_events", [])
            if isinstance(event, Mapping)
        ),
        default=0,
    )
    return max(legacy_sequence, event_sequence) + 1


def build_unified_supervisor_node():
    """Build the only route authority in the unified graph."""

    async def unified_supervisor(
        state: UnifiedEstimationGraphState,
    ) -> Command[UnifiedDestination]:
        destination, reason_code, summary, forced_review = _route(state)
        sequence = _next_sequence(state)
        estimation_id = str(state.get("estimation_id", "unknown")).strip()
        event = UnifiedRouteEvent(
            event_id=(
                f"{estimation_id}:unified-route:{sequence}:"
                f"{destination}:{reason_code}"
            ),
            sequence=sequence,
            destination=destination,
            reason_code=reason_code,
            summary=summary,
        )
        update = UnifiedEstimationGraphState(
            unified_policy_version=_POLICY_VERSION,
            unified_phase=_PHASE_BY_DESTINATION[destination],
            unified_route_events=[event],
            routing_steps=sequence,
        )
        if forced_review:
            update["review_required"] = True
            if state.get("status") == "validated":
                update["status"] = "needs_review"
        return Command(goto=destination, update=update)

    return unified_supervisor
