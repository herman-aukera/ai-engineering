"""Reviewed-graph validation over the latest recalculated evidence state."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping

from app.generation.graph.nodes.validate_and_consolidate import (
    build_validate_and_consolidate_node,
)
from app.generation.graph.review_state import ReviewedEstimationGraphState

ReviewedValidationNode = Callable[
    [ReviewedEstimationGraphState],
    Awaitable[ReviewedEstimationGraphState],
]


def _grounding_statuses(
    state: ReviewedEstimationGraphState,
) -> set[str]:
    return {
        str(estimate.get("grounding_status"))
        for estimate in state.get("component_estimates", [])
        if isinstance(estimate, Mapping) and estimate.get("grounding_status")
    }


def _issue_is_superseded(
    *,
    code: str,
    grounding_statuses: set[str],
    after_recovery: bool,
    explicitly_resolved: set[str],
) -> bool:
    if code in explicitly_resolved:
        return True
    if code == "missing_component_evidence":
        return "no_data" not in grounding_statuses
    if code == "low_confidence_component_estimate":
        return "low_confidence" not in grounding_statuses
    if code == "conflicting_component_evidence":
        return "conflict" not in grounding_statuses
    if code == "estimate_total_mismatch" and after_recovery:
        return True
    return False


def build_reviewed_validation_node(
    *,
    rebuild_aggregate: bool,
) -> ReviewedValidationNode:
    """Adapt append-only mandatory issues to the latest reviewed graph state."""

    mandatory_validation = build_validate_and_consolidate_node()

    async def reviewed_validation(
        state: ReviewedEstimationGraphState,
    ) -> ReviewedEstimationGraphState:
        grounding_statuses = _grounding_statuses(state)
        explicitly_resolved = {
            str(code) for code in state.get("resolved_issue_codes", [])
        }
        after_recovery = state.get("recovery_status") in {
            "completed",
            "partial",
            "failed",
            "skipped",
        }

        retained_issues: list[dict[str, object]] = []
        newly_resolved: list[str] = []
        for issue in state.get("errors", []):
            if not isinstance(issue, Mapping):
                retained_issues.append(dict(issue))
                continue
            code = str(issue.get("code") or "")
            if _issue_is_superseded(
                code=code,
                grounding_statuses=grounding_statuses,
                after_recovery=after_recovery,
                explicitly_resolved=explicitly_resolved,
            ):
                if code:
                    newly_resolved.append(code)
                continue
            retained_issues.append(dict(issue))

        validation_state = ReviewedEstimationGraphState(**dict(state))
        validation_state["errors"] = retained_issues
        validation_state["review_required"] = bool(retained_issues) or bool(
            grounding_statuses & {"no_data", "low_confidence", "conflict"}
        )
        if rebuild_aggregate:
            validation_state.pop("estimate", None)

        update = ReviewedEstimationGraphState(
            **dict(await mandatory_validation(validation_state))
        )
        resolved_issue_codes = list(
            dict.fromkeys(
                [
                    *state.get("resolved_issue_codes", []),
                    *newly_resolved,
                ]
            )
        )
        if resolved_issue_codes:
            update["resolved_issue_codes"] = resolved_issue_codes
        return update

    return reviewed_validation
