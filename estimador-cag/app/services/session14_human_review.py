"""Deterministic Session 14 reliability assessment and safe projections."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite

from app.schemas.session14_human_review import (
    HistoricalRangeStatus,
    Session14HumanReviewActionRecord,
    Session14HumanReviewDecision,
    Session14HumanReviewReasonCode,
)

DEFAULT_SESSION14_CONFIDENCE_THRESHOLD = 0.65


@dataclass(frozen=True)
class Session14ReviewAssessment:
    """Small policy result safe to persist or expose in an interrupt."""

    required: bool
    reason_codes: tuple[Session14HumanReviewReasonCode, ...]
    confidence: float | None
    historical_range_status: HistoricalRangeStatus
    evidence_count: int
    active_findings: tuple[str, ...]


def _component_estimates(
    state: Mapping[str, object],
) -> list[Mapping[str, object]]:
    raw_estimates = state.get("component_estimates", [])
    if not isinstance(raw_estimates, list):
        return []
    return [
        item for item in raw_estimates if isinstance(item, Mapping)
    ]


def _finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    normalized = float(value)
    return normalized if isfinite(normalized) else None


def _confidence(
    estimates: Sequence[Mapping[str, object]],
) -> float | None:
    values = [
        normalized
        for estimate in estimates
        if (normalized := _finite_number(estimate.get("confidence")))
        is not None
        and 0 <= normalized <= 1
    ]
    return min(values) if values else None


def _is_human_adjustment(estimate: Mapping[str, object]) -> bool:
    return estimate.get("derivation_method") == "human_adjustment"


def _has_no_precedent(estimate: Mapping[str, object]) -> bool:
    if _is_human_adjustment(estimate):
        return False
    if estimate.get("grounding_status") == "no_data":
        return True
    source_hours = estimate.get("source_hours")
    references = estimate.get("reference_budget_ids")
    return not isinstance(source_hours, list) or not source_hours or (
        not isinstance(references, list) or not references
    )


def _is_outside_historical_range(
    estimate: Mapping[str, object],
) -> bool:
    hours = _finite_number(estimate.get("hours"))
    low = _finite_number(estimate.get("source_range_low"))
    high = _finite_number(estimate.get("source_range_high"))
    return (
        hours is not None
        and low is not None
        and high is not None
        and (hours < low or hours > high)
    )


def _historical_range_status(
    estimates: Sequence[Mapping[str, object]],
) -> HistoricalRangeStatus:
    if any(_is_outside_historical_range(item) for item in estimates):
        return "outside_range"
    if not estimates or any(
        (
            _finite_number(item.get("source_range_low")) is None
            or _finite_number(item.get("source_range_high")) is None
        )
        for item in estimates
    ):
        return "unavailable"
    return "within_range"


def _active_findings(state: Mapping[str, object]) -> tuple[str, ...]:
    errors = state.get("errors", [])
    if not isinstance(errors, list):
        return ()
    return tuple(
        dict.fromkeys(
            str(error.get("code"))
            for error in errors
            if isinstance(error, Mapping) and error.get("code")
        )
    )


def assess_session14_human_review(
    state: Mapping[str, object],
    *,
    confidence_threshold: float = (
        DEFAULT_SESSION14_CONFIDENCE_THRESHOLD
    ),
) -> Session14ReviewAssessment:
    """Apply the mandatory Task 14 pause triggers deterministically."""

    if not 0 <= confidence_threshold <= 1:
        raise ValueError(
            "confidence_threshold must be between zero and one"
        )

    estimates = _component_estimates(state)
    confidence = _confidence(estimates)
    range_status = _historical_range_status(estimates)
    reason_codes: list[Session14HumanReviewReasonCode] = []

    if confidence is not None and confidence < confidence_threshold:
        reason_codes.append("low_confidence")
    if any(
        not _is_human_adjustment(item)
        and _is_outside_historical_range(item)
        for item in estimates
    ):
        reason_codes.append("outside_historical_range")
    if not estimates or any(_has_no_precedent(item) for item in estimates):
        reason_codes.append("no_precedent")

    route_reason = state.get("route_reason_code")
    if route_reason == "routing_budget_exhausted":
        reason_codes.append("routing_budget_exhausted")

    if state.get("review_required") is True and not reason_codes:
        reason_codes.append("validation_requires_review")

    matches = state.get("budget_matches", [])
    evidence_count = len(matches) if isinstance(matches, list) else 0

    return Session14ReviewAssessment(
        required=bool(reason_codes),
        reason_codes=tuple(reason_codes),
        confidence=confidence,
        historical_range_status=range_status,
        evidence_count=evidence_count,
        active_findings=_active_findings(state),
    )


def build_session14_interrupt_payload(
    state: Mapping[str, object],
    *,
    assessment: Session14ReviewAssessment,
    revision: int,
) -> dict[str, object]:
    """Project only allow-listed review data into the interrupt payload."""

    estimation_id = str(state.get("estimation_id") or "").strip()
    thread_id = str(state.get("thread_id") or "").strip()
    estimate = state.get("estimate")
    estimate_mapping = estimate if isinstance(estimate, Mapping) else {}
    component_estimates = _component_estimates(state)

    return {
        "gate": "session14_human_review",
        "estimation_id": estimation_id,
        "thread_id": thread_id or f"estimate:{estimation_id}",
        "revision": revision,
        "reason_codes": list(assessment.reason_codes),
        "estimate_summary": {
            "total_hours": estimate_mapping.get("total_hours"),
            "component_count": len(component_estimates),
        },
        "confidence": assessment.confidence,
        "historical_range_status": (
            assessment.historical_range_status
        ),
        "evidence_count": assessment.evidence_count,
        "active_findings": list(assessment.active_findings),
        "allowed_actions": ["approve", "adjust", "reject"],
    }


def action_record_matches_decision(
    record: Mapping[str, object],
    decision: Session14HumanReviewDecision,
) -> bool:
    """Return whether a persisted action is the exact same request."""

    adjustments = [
        item.model_dump(mode="json")
        for item in decision.adjustments or []
    ]
    return (
        record.get("idempotency_key") == decision.idempotency_key
        and record.get("action") == decision.action
        and record.get("actor") == decision.actor
        and record.get("reason") == decision.reason
        and record.get("revision") == decision.expected_revision
        and record.get("adjustments") == adjustments
    )


def action_record_from_decision(
    *,
    estimation_id: str,
    decision: Session14HumanReviewDecision,
) -> Session14HumanReviewActionRecord:
    """Build one sanitized action ledger entry."""

    return Session14HumanReviewActionRecord(
        action_id=(
            f"{estimation_id}:human-review:"
            f"{decision.expected_revision}:"
            f"{decision.idempotency_key}"
        ),
        idempotency_key=decision.idempotency_key,
        action=decision.action,
        actor=decision.actor,
        reason=decision.reason,
        revision=decision.expected_revision,
        adjustments=[
            item.model_dump(mode="json")
            for item in decision.adjustments or []
        ],
    )
