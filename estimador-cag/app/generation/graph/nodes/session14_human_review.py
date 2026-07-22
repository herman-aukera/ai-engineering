"""Persistent Session 14 human-review gate and deterministic resume actions."""

from __future__ import annotations

from copy import deepcopy
from typing import Literal

from langgraph.types import Command, interrupt

from app.generation.graph.review_state import (
    Session14EstimationGraphState,
)
from app.schemas.session14_human_review import (
    Session14HumanReviewDecision,
)
from app.services.session14_human_review import (
    DEFAULT_SESSION14_CONFIDENCE_THRESHOLD,
    action_record_from_decision,
    assess_session14_human_review,
    build_session14_interrupt_payload,
)


class StaleSession14HumanReviewError(ValueError):
    """Raised when a decision targets an obsolete review revision."""


class IncompleteSession14AdjustmentError(ValueError):
    """Raised when an adjustment leaves mandatory review triggers active."""


def _revision(state: Session14EstimationGraphState) -> int:
    value = state.get("human_review_revision", 1)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("human_review_revision must be a positive integer")
    return value


def _estimation_id(state: Session14EstimationGraphState) -> str:
    value = state.get("estimation_id")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("estimation_id must not be blank")
    return value.strip()


def _apply_adjustments(
    state: Session14EstimationGraphState,
    decision: Session14HumanReviewDecision,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    raw_estimates = state.get("component_estimates")
    if not isinstance(raw_estimates, list) or not raw_estimates:
        raise IncompleteSession14AdjustmentError(
            "adjust requires component estimates"
        )

    estimates = [deepcopy(dict(item)) for item in raw_estimates]
    by_id = {
        str(item.get("component_id")): item
        for item in estimates
        if isinstance(item, dict) and item.get("component_id")
    }

    for adjustment in decision.adjustments or []:
        estimate = by_id.get(adjustment.component_id)
        if estimate is None:
            raise IncompleteSession14AdjustmentError(
                "unknown adjustment component_id: "
                f"{adjustment.component_id}"
            )
        estimate.update(
            {
                "hours": adjustment.hours,
                "grounding_status": "grounded",
                "confidence": 1.0,
                "derivation_method": "human_adjustment",
                "review_reasons": [],
            }
        )

    hours: list[float] = []
    for estimate in estimates:
        value = estimate.get("hours")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise IncompleteSession14AdjustmentError(
                "adjust must resolve hours for every component"
            )
        hours.append(float(value))

    subtotal = round(sum(hours), 2)
    aggregate = {
        "components": deepcopy(estimates),
        "subtotal_hours": subtotal,
        "contingency_hours": 0.0,
        "total_hours": subtotal,
        "total_cost_eur": None,
        "currency": "EUR",
    }
    return estimates, aggregate


def _decision_trace_events(
    *,
    decision: Session14HumanReviewDecision,
    reason_codes: list[str],
) -> list[dict[str, object]]:
    evidence_refs = list(
        dict.fromkeys(
            reference
            for adjustment in decision.adjustments or []
            for reference in adjustment.evidence_refs
        )
    )
    return [
        {
            "event_type": "session14_human_review_paused",
            "node": "human_review_gate",
            "summary": (
                "Execution paused for a persisted human review decision."
            ),
            "evidence_refs": [],
            "state_delta_keys": [
                "human_review_status",
                "human_review_reason_codes",
                "trace_events",
            ],
        },
        {
            "event_type": f"session14_human_review_{decision.action}",
            "node": "human_review_gate",
            "summary": (
                "Human review recorded action "
                f"{decision.action} for {len(reason_codes)} reason codes."
            ),
            "evidence_refs": evidence_refs,
            "state_delta_keys": [
                "human_review_revision",
                "human_review_status",
                "human_review_actions",
                "status",
                "review_required",
                "trace_events",
            ],
        },
    ]


def build_session14_human_review_gate(
    *,
    confidence_threshold: float = (
        DEFAULT_SESSION14_CONFIDENCE_THRESHOLD
    ),
):
    """Build the deterministic interrupt/resume gate for Task 14."""

    async def human_review_gate(
        state: Session14EstimationGraphState,
    ) -> Command[Literal["finalize"]]:
        assessment = assess_session14_human_review(
            state,
            confidence_threshold=confidence_threshold,
        )

        if not assessment.required:
            return Command(
                goto="finalize",
                update=Session14EstimationGraphState(
                    previous_agent=state.get("current_agent"),
                    current_agent="human_review_gate",
                    next_agent="finalize",
                    confidence=assessment.confidence,
                    historical_range_status=(
                        assessment.historical_range_status
                    ),
                    human_review_status="not_requested",
                    human_review_reason_codes=[],
                ),
            )

        revision = _revision(state)
        raw_decision = interrupt(
            build_session14_interrupt_payload(
                state,
                assessment=assessment,
                revision=revision,
            )
        )
        decision = Session14HumanReviewDecision.model_validate(
            raw_decision
        )

        if decision.expected_revision != revision:
            raise StaleSession14HumanReviewError(
                "human review revision "
                f"{decision.expected_revision} does not match {revision}"
            )

        estimation_id = _estimation_id(state)
        reason_codes = list(assessment.reason_codes)
        update = Session14EstimationGraphState(
            previous_agent=state.get("current_agent"),
            current_agent="human_review_gate",
            next_agent="finalize",
            human_review_revision=revision + 1,
            human_review_reason_codes=reason_codes,
            human_review_actions=[
                action_record_from_decision(
                    estimation_id=estimation_id,
                    decision=decision,
                )
            ],
            confidence=assessment.confidence,
            historical_range_status=(
                assessment.historical_range_status
            ),
            trace_events=_decision_trace_events(
                decision=decision,
                reason_codes=reason_codes,
            ),
        )

        if decision.action == "approve":
            validation = state.get("validation")
            is_coherent = bool(
                validation.get("is_coherent")
                if isinstance(validation, dict)
                else False
            )
            update.update(
                human_review_status="approved",
                status="validated",
                review_required=False,
                validation={
                    "is_coherent": is_coherent,
                    "review_required": False,
                    "status": "validated",
                    "human_authorized": True,
                },
            )
        elif decision.action == "reject":
            update.update(
                human_review_status="rejected",
                status="needs_review",
                review_required=True,
            )
        else:
            estimates, estimate = _apply_adjustments(
                state,
                decision,
            )
            candidate = {
                **dict(state),
                "component_estimates": estimates,
                "estimate": estimate,
                "review_required": False,
                "route_reason_code": None,
            }
            adjusted_assessment = assess_session14_human_review(
                candidate,
                confidence_threshold=confidence_threshold,
            )
            if adjusted_assessment.required:
                joined_reasons = ", ".join(
                    adjusted_assessment.reason_codes
                )
                raise IncompleteSession14AdjustmentError(
                    "adjustment leaves review triggers active: "
                    f"{joined_reasons}"
                )
            update.update(
                human_review_status="adjusted",
                status="validated",
                review_required=False,
                component_estimates=estimates,
                estimate=estimate,
                confidence=adjusted_assessment.confidence,
                historical_range_status=(
                    adjusted_assessment.historical_range_status
                ),
                validation={
                    "is_coherent": True,
                    "review_required": False,
                    "status": "validated",
                    "human_authorized": True,
                },
            )

        return Command(goto="finalize", update=update)

    return human_review_gate
