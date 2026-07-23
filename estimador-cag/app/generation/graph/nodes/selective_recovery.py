"""Selective recovery node for unresolved or low-confidence components."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping

from app.generation.graph.review_state import ReviewedEstimationGraphState
from app.generation.graph.state import ComponentItem
from app.services.selective_recovery import SelectiveRecoveryApplication

SelectiveRecoveryNode = Callable[
    [ReviewedEstimationGraphState],
    Awaitable[ReviewedEstimationGraphState],
]


def _flagged_components(
    state: ReviewedEstimationGraphState,
) -> list[ComponentItem]:
    flagged_ids = {
        str(estimate.get("component_id"))
        for estimate in state.get("component_estimates", [])
        if isinstance(estimate, Mapping)
        and estimate.get("grounding_status") in {"no_data", "low_confidence"}
        and estimate.get("component_id")
    }
    return [
        ComponentItem(**dict(component))
        for component in state.get("components", [])
        if isinstance(component, Mapping)
        and str(component.get("component_id")) in flagged_ids
    ]


def _event(
    *,
    event_type: str,
    summary: str,
    evidence_refs: list[str],
    state_delta_keys: list[str],
) -> dict[str, object]:
    return {
        "event_type": event_type,
        "node": "selective_recovery",
        "summary": summary,
        "evidence_refs": evidence_refs,
        "state_delta_keys": state_delta_keys,
    }


def build_selective_recovery_node(
    recovery_application: SelectiveRecoveryApplication | None,
) -> SelectiveRecoveryNode:
    """Build a recovery node that never accepts model-authored hours."""

    async def selective_recovery(
        state: ReviewedEstimationGraphState,
    ) -> ReviewedEstimationGraphState:
        flagged = _flagged_components(state)
        flagged_ids = [component["component_id"] for component in flagged]
        if not flagged:
            return {
                "recovery_status": "not_requested",
                "recovery_route": "complete",
                "recovery_flagged_component_ids": [],
                "recovery_recovered_component_ids": [],
                "recovery_unresolved_component_ids": [],
                "trace_events": [
                    _event(
                        event_type="selective_recovery_not_required",
                        summary=(
                            "No no-data or low-confidence components required "
                            "agent-assisted recovery."
                        ),
                        evidence_refs=[],
                        state_delta_keys=[
                            "recovery_status",
                            "recovery_route",
                            "recovery_flagged_component_ids",
                            "recovery_recovered_component_ids",
                            "recovery_unresolved_component_ids",
                            "trace_events",
                        ],
                    )
                ],
            }

        if recovery_application is None:
            return {
                "recovery_status": "skipped",
                "recovery_route": "complete",
                "recovery_flagged_component_ids": flagged_ids,
                "recovery_recovered_component_ids": [],
                "recovery_unresolved_component_ids": flagged_ids,
                "trace_events": [
                    _event(
                        event_type="selective_recovery_unavailable",
                        summary=(
                            "Recovery was required but no bounded recovery runtime "
                            "was configured."
                        ),
                        evidence_refs=flagged_ids,
                        state_delta_keys=[
                            "recovery_status",
                            "recovery_route",
                            "recovery_flagged_component_ids",
                            "recovery_recovered_component_ids",
                            "recovery_unresolved_component_ids",
                            "trace_events",
                        ],
                    )
                ],
            }

        try:
            result = await recovery_application.recover(
                components=flagged,
                existing_matches=state.get("budget_matches", []),
            )
        except Exception as exc:
            return {
                "recovery_status": "failed",
                "recovery_route": "complete",
                "recovery_flagged_component_ids": flagged_ids,
                "recovery_recovered_component_ids": [],
                "recovery_unresolved_component_ids": flagged_ids,
                "errors": [
                    {
                        "code": "selective_recovery_failed",
                        "message": (
                            "Bounded selective recovery failed with "
                            f"{type(exc).__name__}."
                        ),
                        "node": "selective_recovery",
                        "severity": "warning",
                    }
                ],
                "trace_events": [
                    _event(
                        event_type="selective_recovery_failed",
                        summary=(
                            "Selective recovery failed without changing existing "
                            "estimation evidence."
                        ),
                        evidence_refs=flagged_ids,
                        state_delta_keys=[
                            "recovery_status",
                            "recovery_route",
                            "recovery_flagged_component_ids",
                            "recovery_recovered_component_ids",
                            "recovery_unresolved_component_ids",
                            "errors",
                            "trace_events",
                        ],
                    )
                ],
            }

        recovered = result.recovered_component_ids
        unresolved = result.unresolved_component_ids
        status = "completed" if recovered and not unresolved else "partial"
        if not recovered:
            status = "failed"
        route = "recalculate" if result.recovered_matches else "complete"
        state_delta_keys = [
            "recovery_status",
            "recovery_route",
            "recovery_runtime_result",
            "recovery_flagged_component_ids",
            "recovery_recovered_component_ids",
            "recovery_unresolved_component_ids",
            "trace_events",
        ]
        update: ReviewedEstimationGraphState = {
            "recovery_status": status,
            "recovery_route": route,
            "recovery_runtime_result": result.runtime.model_dump(mode="json"),
            "recovery_flagged_component_ids": result.flagged_component_ids,
            "recovery_recovered_component_ids": recovered,
            "recovery_unresolved_component_ids": unresolved,
        }
        if result.recovered_matches:
            update["budget_matches"] = [
                match.model_dump(mode="json")
                for match in result.recovered_matches
            ]
            state_delta_keys.append("budget_matches")
        update["trace_events"] = [
            _event(
                event_type="selective_recovery_completed",
                summary=(
                    f"Recovered evidence for {len(recovered)} of "
                    f"{len(result.flagged_component_ids)} flagged components."
                ),
                evidence_refs=[*recovered, *unresolved],
                state_delta_keys=state_delta_keys,
            )
        ]
        return update

    return selective_recovery
