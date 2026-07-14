"""Fifth required Session 13 node: validate and consolidate the estimate."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from copy import deepcopy
from math import isclose, isfinite
from statistics import median

from app.generation.graph.state import (
    ComponentEstimate,
    EstimationGraphState,
    GraphEstimate,
    GraphIssue,
    GroundingStatus,
)

ValidateAndConsolidateNode = Callable[
    [EstimationGraphState],
    Awaitable[EstimationGraphState],
]

_ALLOWED_GROUNDING_STATUSES = {
    "grounded",
    "low_confidence",
    "conflict",
    "no_data",
}


def _identifier(
    value: object,
    *,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{field_name} must not be blank")

    return normalized


def _string_list(
    value: object,
    *,
    field_name: str,
) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")

    normalized: list[str] = []

    for item in value:
        normalized.append(
            _identifier(
                item,
                field_name=field_name,
            )
        )

    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must not contain duplicates")

    return normalized


def _optional_positive_float(
    value: object,
    *,
    field_name: str,
) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")

    normalized = float(value)

    if not isfinite(normalized) or normalized <= 0:
        raise ValueError(
            f"{field_name} must be finite and positive"
        )

    return normalized


def _optional_non_negative_float(
    value: object,
    *,
    field_name: str,
) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")

    normalized = float(value)

    if not isfinite(normalized) or normalized < 0:
        raise ValueError(
            f"{field_name} must be finite and non-negative"
        )

    return normalized


def _positive_float_list(
    value: object,
    *,
    field_name: str,
) -> list[float]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")

    normalized: list[float] = []

    for item in value:
        item_value = _optional_positive_float(
            item,
            field_name=field_name,
        )
        if item_value is None:
            raise ValueError(
                f"{field_name} must not contain null values"
            )
        normalized.append(item_value)

    return sorted(normalized)


def _grounding_status(value: object) -> GroundingStatus:
    if value not in _ALLOWED_GROUNDING_STATUSES:
        raise ValueError("grounding_status is invalid")

    return value


def _confidence(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("confidence must be numeric")

    normalized = float(value)

    if (
        not isfinite(normalized)
        or normalized < 0
        or normalized > 1
    ):
        raise ValueError(
            "confidence must be between zero and one"
        )

    return normalized


def _validated_component_estimates(
    raw_estimates: object,
) -> list[ComponentEstimate]:
    if not isinstance(raw_estimates, list) or not raw_estimates:
        raise ValueError(
            "component_estimates must be a non-empty list"
        )

    estimates: list[ComponentEstimate] = []
    seen_component_ids: set[str] = set()

    for raw_estimate in raw_estimates:
        if not isinstance(raw_estimate, Mapping):
            raise ValueError(
                "component estimate must be a mapping"
            )

        component_id = _identifier(
            raw_estimate.get("component_id"),
            field_name="component_id",
        )
        name = _identifier(
            raw_estimate.get("name"),
            field_name="name",
        )

        if component_id in seen_component_ids:
            raise ValueError(
                "component estimate identifiers must be unique"
            )

        seen_component_ids.add(component_id)

        status = _grounding_status(
            raw_estimate.get("grounding_status")
        )
        hours = _optional_positive_float(
            raw_estimate.get("hours"),
            field_name="hours",
        )
        reference_budget_ids = _string_list(
            raw_estimate.get("reference_budget_ids"),
            field_name="reference_budget_ids",
        )
        reference_component_ids = _string_list(
            raw_estimate.get("reference_component_ids"),
            field_name="reference_component_ids",
        )
        source_hours = _positive_float_list(
            raw_estimate.get("source_hours"),
            field_name="source_hours",
        )
        range_low = _optional_positive_float(
            raw_estimate.get("source_range_low"),
            field_name="source_range_low",
        )
        range_high = _optional_positive_float(
            raw_estimate.get("source_range_high"),
            field_name="source_range_high",
        )
        dispersion = _optional_non_negative_float(
            raw_estimate.get("dispersion"),
            field_name="dispersion",
        )
        confidence = _confidence(
            raw_estimate.get("confidence")
        )
        derivation_method = _identifier(
            raw_estimate.get("derivation_method"),
            field_name="derivation_method",
        )
        review_reasons = _string_list(
            raw_estimate.get("review_reasons"),
            field_name="review_reasons",
        )

        if status == "no_data":
            if hours is not None:
                raise ValueError(
                    "no-data estimates must not include hours"
                )
            if source_hours:
                raise ValueError(
                    "no-data estimates must not include source hours"
                )
            if range_low is not None or range_high is not None:
                raise ValueError(
                    "no-data estimates must not include a source range"
                )
            if dispersion is not None:
                raise ValueError(
                    "no-data estimates must not include dispersion"
                )
            if confidence != 0.0:
                raise ValueError(
                    "no-data estimates must have zero confidence"
                )
            if not review_reasons:
                raise ValueError(
                    "no-data estimates must explain the review reason"
                )
        else:
            if hours is None:
                raise ValueError(
                    "grounded evidence statuses must include hours"
                )
            if not source_hours:
                raise ValueError(
                    "estimated hours require recorded source hours"
                )
            if not reference_budget_ids:
                raise ValueError(
                    "estimated hours require budget provenance"
                )
            if range_low is None or range_high is None:
                raise ValueError(
                    "estimated hours require a source range"
                )
            if dispersion is None:
                raise ValueError(
                    "estimated hours require dispersion"
                )

            expected_median = float(median(source_hours))
            expected_low = float(min(source_hours))
            expected_high = float(max(source_hours))
            expected_dispersion = round(
                (expected_high - expected_low)
                / expected_median,
                4,
            )

            if not isclose(
                hours,
                expected_median,
                rel_tol=0.0,
                abs_tol=0.01,
            ):
                raise ValueError(
                    "component hours must equal the source median"
                )

            if not isclose(
                range_low,
                expected_low,
                rel_tol=0.0,
                abs_tol=0.01,
            ):
                raise ValueError(
                    "source_range_low is inconsistent"
                )

            if not isclose(
                range_high,
                expected_high,
                rel_tol=0.0,
                abs_tol=0.01,
            ):
                raise ValueError(
                    "source_range_high is inconsistent"
                )

            if not isclose(
                dispersion,
                expected_dispersion,
                rel_tol=0.0,
                abs_tol=0.0001,
            ):
                raise ValueError(
                    "dispersion is inconsistent"
                )

            if status == "grounded" and review_reasons:
                raise ValueError(
                    "grounded estimates must not require review"
                )

            if status != "grounded" and not review_reasons:
                raise ValueError(
                    "non-grounded estimates must explain review"
                )

        estimates.append(
            {
                "component_id": component_id,
                "name": name,
                "hours": hours,
                "grounding_status": status,
                "reference_budget_ids": reference_budget_ids,
                "reference_component_ids": reference_component_ids,
                "source_hours": source_hours,
                "source_range_low": range_low,
                "source_range_high": range_high,
                "dispersion": dispersion,
                "confidence": confidence,
                "derivation_method": derivation_method,
                "review_reasons": review_reasons,
            }
        )

    return estimates


def _canonical_estimate(
    estimates: Sequence[ComponentEstimate],
) -> GraphEstimate:
    known_hours = [
        estimate["hours"]
        for estimate in estimates
        if estimate["hours"] is not None
    ]

    subtotal_hours = (
        round(sum(known_hours), 2)
        if known_hours
        else None
    )
    complete = len(known_hours) == len(estimates)

    return {
        "components": deepcopy(list(estimates)),
        "subtotal_hours": subtotal_hours,
        # Mandatory Session 13 adds no hidden contingency assumption.
        "contingency_hours": 0.0 if complete else None,
        "total_hours": subtotal_hours if complete else None,
        # Cost remains unresolved until an explicit rate is configured.
        "total_cost_eur": None,
        "currency": "EUR",
    }


def _optional_number_equal(
    left: object,
    right: float | None,
) -> bool:
    if left is None or right is None:
        return left is None and right is None

    if isinstance(left, bool) or not isinstance(left, (int, float)):
        return False

    left_value = float(left)

    return (
        isfinite(left_value)
        and isclose(
            left_value,
            right,
            rel_tol=0.0,
            abs_tol=0.01,
        )
    )


def _existing_estimate_matches(
    existing: object,
    canonical: GraphEstimate,
) -> bool:
    if existing is None:
        return True

    if not isinstance(existing, Mapping):
        return False

    if existing.get("components") != canonical["components"]:
        return False

    if existing.get("currency") != canonical["currency"]:
        return False

    for field_name in (
        "subtotal_hours",
        "contingency_hours",
        "total_hours",
        "total_cost_eur",
    ):
        if not _optional_number_equal(
            existing.get(field_name),
            canonical[field_name],
        ):
            return False

    return True


def _existing_issues(
    state: EstimationGraphState,
) -> list[GraphIssue]:
    raw_issues = state.get("errors", [])

    if not isinstance(raw_issues, list):
        raise ValueError("errors must be a list")

    issues: list[GraphIssue] = []

    for raw_issue in raw_issues:
        if not isinstance(raw_issue, Mapping):
            raise ValueError("error entries must be mappings")

        code = _identifier(
            raw_issue.get("code"),
            field_name="error code",
        )
        message = _identifier(
            raw_issue.get("message"),
            field_name="error message",
        )
        node = _identifier(
            raw_issue.get("node"),
            field_name="error node",
        )
        severity = raw_issue.get("severity")

        if severity not in {"warning", "error"}:
            raise ValueError("error severity is invalid")

        issues.append(
            {
                "code": code,
                "message": message,
                "node": node,
                "severity": severity,
            }
        )

    return issues


def _evidence_refs(
    estimates: Sequence[ComponentEstimate],
) -> list[str]:
    values = [
        *[
            estimate["component_id"]
            for estimate in estimates
        ],
        *[
            budget_id
            for estimate in estimates
            for budget_id in estimate["reference_budget_ids"]
        ],
    ]
    return list(dict.fromkeys(values))


def _empty_estimate() -> GraphEstimate:
    return {
        "components": [],
        "subtotal_hours": None,
        "contingency_hours": None,
        "total_hours": None,
        "total_cost_eur": None,
        "currency": "EUR",
    }


def _failure_update(
    *,
    code: str,
    message: str,
) -> EstimationGraphState:
    return {
        "estimate": _empty_estimate(),
        "status": "needs_review",
        "review_required": True,
        "errors": [
            {
                "code": code,
                "message": message,
                "node": "validate_and_consolidate",
                "severity": "error",
            }
        ],
        "trace_events": [
            {
                "event_type": "estimate_validation_failed",
                "node": "validate_and_consolidate",
                "summary": (
                    "The component estimate contract failed validation."
                ),
                "evidence_refs": [],
                "state_delta_keys": [
                    "estimate",
                    "status",
                    "review_required",
                    "errors",
                    "trace_events",
                ],
            }
        ],
    }


def build_validate_and_consolidate_node(
) -> ValidateAndConsolidateNode:
    """Create the deterministic terminal validation node."""

    async def validate_and_consolidate(
        state: EstimationGraphState,
    ) -> EstimationGraphState:
        raw_estimates = state.get("component_estimates")

        if not isinstance(raw_estimates, list) or not raw_estimates:
            return _failure_update(
                code="missing_component_estimates",
                message=(
                    "No component estimates are available "
                    "for consolidation."
                ),
            )

        try:
            estimates = _validated_component_estimates(
                raw_estimates
            )
            existing_issues = _existing_issues(state)
        except (AttributeError, KeyError, TypeError, ValueError):
            return _failure_update(
                code="invalid_component_estimates",
                message=(
                    "Component estimates or prior issues "
                    "failed deterministic validation."
                ),
            )

        canonical = _canonical_estimate(estimates)

        mismatch = not _existing_estimate_matches(
            state.get("estimate"),
            canonical,
        )

        new_issues: list[GraphIssue] = []

        if mismatch:
            new_issues.append(
                {
                    "code": "estimate_total_mismatch",
                    "message": (
                        "A pre-existing aggregate estimate did not match "
                        "the component-derived arithmetic."
                    ),
                    "node": "validate_and_consolidate",
                    "severity": "error",
                }
            )

        review_component_ids = [
            estimate["component_id"]
            for estimate in estimates
            if estimate["grounding_status"] != "grounded"
        ]

        needs_review = any(
            (
                state.get("review_required") is True,
                bool(existing_issues),
                bool(review_component_ids),
                bool(new_issues),
            )
        )

        if needs_review:
            status = "needs_review"
            event_type = "estimate_needs_review"
            summary = (
                f"Consolidated {len(estimates)} component estimates; "
                f"{len(review_component_ids)} requires review."
            )
            state_delta_keys = [
                "estimate",
                "status",
                "review_required",
                "trace_events",
            ]

            if new_issues:
                state_delta_keys.insert(3, "errors")
        else:
            status = "validated"
            event_type = "estimate_validated"
            summary = (
                f"Validated {len(estimates)} grounded "
                f"component estimates totaling "
                f"{canonical['total_hours']} hours."
            )
            state_delta_keys = [
                "estimate",
                "status",
                "review_required",
                "trace_events",
            ]

        update: EstimationGraphState = {
            "estimate": canonical,
            "status": status,
            "review_required": needs_review,
            "trace_events": [
                {
                    "event_type": event_type,
                    "node": "validate_and_consolidate",
                    "summary": summary,
                    "evidence_refs": _evidence_refs(estimates),
                    "state_delta_keys": state_delta_keys,
                }
            ],
        }

        # Reducer invariant: return only newly discovered validation issues.
        if new_issues:
            update["errors"] = new_issues

        return update

    return validate_and_consolidate
