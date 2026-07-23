"""Durable final-estimate human gate with typed audit-safe overrides."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy

from langgraph.types import interrupt

from app.generation.graph.review_state import ReviewedEstimationGraphState
from app.schemas.human_review import FinalEstimateReviewDecision


class StaleFinalEstimateReviewError(ValueError):
    """Raised when a final review targets an obsolete revision."""


def _requires_gate(state: ReviewedEstimationGraphState) -> bool:
    mode = state.get("human_review_mode", "risk_based")
    if mode == "disabled":
        return False
    if mode == "required":
        return True
    decision = state.get("boss_decision", {})
    action = decision.get("action") if isinstance(decision, Mapping) else None
    return bool(state.get("review_required")) or action in {"human_review", "reject"}


def _override_estimates(
    state: ReviewedEstimationGraphState,
    decision: FinalEstimateReviewDecision,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    estimates = deepcopy(state.get("component_estimates", []))
    by_id = {
        str(item.get("component_id")): item
        for item in estimates
        if isinstance(item, dict)
    }
    changes: list[dict[str, object]] = []
    for baseline in decision.overrides or []:
        estimate = by_id.get(baseline.component_id)
        if estimate is None:
            raise ValueError(f"unknown override component_id: {baseline.component_id}")
        old_hours = estimate.get("hours")
        estimate.update(
            {
                "hours": baseline.hours,
                "grounding_status": "grounded",
                "confidence": 1.0,
                "derivation_method": "human_baseline_override",
                "review_reasons": [],
            }
        )
        changes.append(
            {
                "component_id": baseline.component_id,
                "field": "hours",
                "old_value": old_hours,
                "new_value": baseline.hours,
                "evidence_refs": baseline.evidence_refs,
            }
        )
    return estimates, changes


def build_final_estimate_review_node():
    """Build the checkpoint-safe final review interrupt node."""

    async def final_estimate_review(
        state: ReviewedEstimationGraphState,
    ) -> ReviewedEstimationGraphState:
        revision = int(state.get("final_review_revision", 0))
        if not _requires_gate(state):
            return {
                "final_review_status": "skipped",
                "final_review_route": "complete",
                "trace_events": [
                    {
                        "event_type": "final_estimate_review_skipped",
                        "node": "final_estimate_review",
                        "summary": "Final estimate gate was not required by policy.",
                        "evidence_refs": [],
                        "state_delta_keys": [
                            "final_review_status",
                            "final_review_route",
                            "trace_events",
                        ],
                    }
                ],
            }

        raw_decision = interrupt(
            {
                "gate": "final_estimate_review",
                "revision": revision,
                "estimate": deepcopy(state.get("estimate", {})),
                "component_estimates": deepcopy(state.get("component_estimates", [])),
                "critic_report": deepcopy(state.get("critic_report", {})),
                "boss_decision": deepcopy(state.get("boss_decision", {})),
                "allowed_actions": ["approve", "reject", "request_recovery", "override"],
            }
        )
        decision = FinalEstimateReviewDecision.model_validate(raw_decision)
        if decision.expected_revision != revision:
            raise StaleFinalEstimateReviewError(
                f"final estimate review revision {decision.expected_revision} does not match {revision}"
            )

        next_revision = revision + 1
        record: dict[str, object] = {
            "action": decision.action,
            "actor": decision.actor,
            "reason": decision.reason,
            "revision": next_revision,
            "changes": [],
        }
        update: ReviewedEstimationGraphState = {
            "final_review_revision": next_revision,
            "final_review_record": record,
            "trace_events": [
                {
                    "event_type": f"final_estimate_{decision.action}",
                    "node": "final_estimate_review",
                    "summary": f"Final estimate review recorded action {decision.action}.",
                    "evidence_refs": [decision.actor],
                    "state_delta_keys": [
                        "final_review_revision",
                        "final_review_record",
                        "final_review_status",
                        "final_review_route",
                        "trace_events",
                    ],
                }
            ],
        }
        if decision.action == "approve":
            update.update(final_review_status="approved", final_review_route="complete")
        elif decision.action == "reject":
            update.update(
                final_review_status="rejected",
                final_review_route="stop",
                status="needs_review",
                review_required=True,
            )
        elif decision.action == "request_recovery":
            update.update(
                final_review_status="recovery_requested",
                final_review_route="recover",
                status="pending",
                review_required=True,
            )
        else:
            estimates, changes = _override_estimates(state, decision)
            record["changes"] = changes
            update.update(
                final_review_status="overridden",
                final_review_route="complete",
                component_estimates=estimates,
                human_baseline_overrides=changes,
                review_required=False,
            )
        return update

    return final_estimate_review
