"""Fourth required Session 13 graph node: deterministic estimation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from statistics import median

from app.generation.graph.ports import (
    EstimationPolicy,
    GraphNodeDependencies,
)
from app.generation.graph.state import (
    ComponentEstimate,
    ComponentItem,
    EstimationGraphState,
    GraphIssue,
    GroundingStatus,
)

GenerateEstimateNode = Callable[
    [EstimationGraphState],
    Awaitable[EstimationGraphState],
]


@dataclass(frozen=True)
class _EvidenceRecord:
    component_id: str
    budget_id: str
    reference_component_id: str | None
    source_document_id: str
    source_chunk_id: str
    recorded_hours: float | None


def _normalize_identifier(
    value: object,
    *,
    field_name: str,
) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError(f"{field_name} must be a string or integer")

    normalized = str(value).strip()

    if not normalized:
        raise ValueError(f"{field_name} must not be blank")

    return normalized


def _normalize_optional_identifier(
    value: object,
    *,
    field_name: str,
) -> str | None:
    if value is None:
        return None

    return _normalize_identifier(
        value,
        field_name=field_name,
    )


def _validated_components(
    raw_components: object,
) -> list[ComponentItem]:
    if not isinstance(raw_components, list) or not raw_components:
        raise ValueError("components must be a non-empty list")

    components: list[ComponentItem] = []
    seen_ids: set[str] = set()

    for raw_component in raw_components:
        if not isinstance(raw_component, Mapping):
            raise ValueError("component must be a mapping")

        component_id = _normalize_identifier(
            raw_component.get("component_id"),
            field_name="component_id",
        )
        name = raw_component.get("name")

        if not isinstance(name, str) or not name.strip():
            raise ValueError("component name must not be blank")

        if component_id in seen_ids:
            raise ValueError("component_id must be unique")

        seen_ids.add(component_id)

        component = dict(raw_component)
        component["component_id"] = component_id
        component["name"] = name.strip()
        components.append(component)

    return components


def _validated_evidence(
    raw_matches: object,
    *,
    known_component_ids: set[str],
) -> list[_EvidenceRecord]:
    if raw_matches is None:
        return []

    if not isinstance(raw_matches, list):
        raise ValueError("budget_matches must be a list")

    evidence: list[_EvidenceRecord] = []
    seen_provenance: set[
        tuple[str, str, str | None, str, str]
    ] = set()

    for raw_match in raw_matches:
        if not isinstance(raw_match, Mapping):
            raise ValueError("budget match must be a mapping")

        component_id = _normalize_identifier(
            raw_match.get("component_id"),
            field_name="component_id",
        )

        if component_id not in known_component_ids:
            raise ValueError(
                "budget evidence references an unknown component"
            )

        budget_id = _normalize_identifier(
            raw_match.get("budget_id"),
            field_name="budget_id",
        )
        reference_component_id = _normalize_optional_identifier(
            raw_match.get("reference_component_id"),
            field_name="reference_component_id",
        )
        source_document_id = _normalize_identifier(
            raw_match.get("source_document_id"),
            field_name="source_document_id",
        )
        source_chunk_id = _normalize_identifier(
            raw_match.get("source_chunk_id"),
            field_name="source_chunk_id",
        )

        raw_hours = raw_match.get("recorded_hours")

        if raw_hours is None:
            recorded_hours = None
        else:
            if (
                isinstance(raw_hours, bool)
                or not isinstance(raw_hours, (int, float))
            ):
                raise ValueError("recorded_hours must be numeric")

            recorded_hours = float(raw_hours)

            if not isfinite(recorded_hours) or recorded_hours <= 0:
                raise ValueError(
                    "recorded_hours must be finite and positive"
                )

        provenance = (
            component_id,
            budget_id,
            reference_component_id,
            source_document_id,
            source_chunk_id,
        )

        if provenance in seen_provenance:
            raise ValueError("budget evidence provenance is duplicated")

        seen_provenance.add(provenance)

        evidence.append(
            _EvidenceRecord(
                component_id=component_id,
                budget_id=budget_id,
                reference_component_id=reference_component_id,
                source_document_id=source_document_id,
                source_chunk_id=source_chunk_id,
                recorded_hours=recorded_hours,
            )
        )

    return evidence


def _confidence(
    *,
    sample_count: int,
    dispersion: float,
) -> float:
    sample_score = min(
        1.0,
        0.5 + (0.25 * max(0, sample_count - 1)),
    )
    dispersion_penalty = min(dispersion, 1.0) * 0.5
    return round(
        max(0.0, sample_score - dispersion_penalty),
        2,
    )


def _grounding(
    *,
    sample_count: int,
    dispersion: float,
    policy: EstimationPolicy,
) -> tuple[GroundingStatus, list[str]]:
    if sample_count < policy.minimum_grounded_samples:
        return (
            "low_confidence",
            [
                "Only one recorded-hours reference was available."
            ],
        )

    if dispersion >= policy.conflict_dispersion_ratio:
        return (
            "conflict",
            [
                (
                    "Reference-hour dispersion is at or above "
                    "the conflict threshold."
                )
            ],
        )

    if dispersion >= policy.low_confidence_dispersion_ratio:
        return (
            "low_confidence",
            [
                (
                    "Reference-hour dispersion is above "
                    "the low-confidence threshold."
                )
            ],
        )

    return "grounded", []


def _component_estimate(
    component: ComponentItem,
    *,
    evidence: Sequence[_EvidenceRecord],
    policy: EstimationPolicy,
) -> ComponentEstimate:
    reference_budget_ids = sorted(
        {item.budget_id for item in evidence}
    )
    reference_component_ids = sorted(
        {
            item.reference_component_id
            for item in evidence
            if item.reference_component_id is not None
        }
    )
    source_hours = sorted(
        item.recorded_hours
        for item in evidence
        if item.recorded_hours is not None
    )

    if not source_hours:
        return {
            "component_id": component["component_id"],
            "name": component["name"],
            "hours": None,
            "grounding_status": "no_data",
            "reference_budget_ids": reference_budget_ids,
            "reference_component_ids": reference_component_ids,
            "source_hours": [],
            "source_range_low": None,
            "source_range_high": None,
            "dispersion": None,
            "confidence": 0.0,
            "derivation_method": "no_recorded_hours",
            "review_reasons": [
                "No recorded hours were available."
            ],
        }

    estimated_hours = round(float(median(source_hours)), 2)
    low = float(min(source_hours))
    high = float(max(source_hours))
    dispersion = round(
        (high - low) / estimated_hours,
        4,
    )

    grounding_status, review_reasons = _grounding(
        sample_count=len(source_hours),
        dispersion=dispersion,
        policy=policy,
    )

    return {
        "component_id": component["component_id"],
        "name": component["name"],
        "hours": estimated_hours,
        "grounding_status": grounding_status,
        "reference_budget_ids": reference_budget_ids,
        "reference_component_ids": reference_component_ids,
        "source_hours": source_hours,
        "source_range_low": low,
        "source_range_high": high,
        "dispersion": dispersion,
        "confidence": _confidence(
            sample_count=len(source_hours),
            dispersion=dispersion,
        ),
        "derivation_method": "median_recorded_hours",
        "review_reasons": review_reasons,
    }


def _issue_for_estimate(
    estimate: ComponentEstimate,
) -> GraphIssue | None:
    component_id = estimate["component_id"]
    grounding_status = estimate["grounding_status"]

    if grounding_status == "grounded":
        return None

    if grounding_status == "no_data":
        return {
            "code": "missing_component_evidence",
            "message": (
                f"Component {component_id} has no "
                "recorded-hours evidence."
            ),
            "node": "generate_estimate",
            "severity": "warning",
        }

    if grounding_status == "conflict":
        return {
            "code": "conflicting_component_evidence",
            "message": (
                f"Component {component_id} has conflicting "
                "recorded-hours evidence."
            ),
            "node": "generate_estimate",
            "severity": "error",
        }

    return {
        "code": "low_confidence_component_estimate",
        "message": (
            f"Component {component_id} has "
            "low-confidence budget evidence."
        ),
        "node": "generate_estimate",
        "severity": "warning",
    }


def _execution_metadata(
    state: EstimationGraphState,
    *,
    component_estimate_count: int,
) -> dict[str, str | int]:
    metadata: dict[str, str | int] = dict(
        state.get("execution_metadata", {})
    )
    metadata["component_estimate_count"] = (
        component_estimate_count
    )
    return metadata


def _failure_update(
    state: EstimationGraphState,
    *,
    code: str,
    message: str,
) -> EstimationGraphState:
    return {
        "component_estimates": [],
        "review_required": True,
        "errors": [
            {
                "code": code,
                "message": message,
                "node": "generate_estimate",
                "severity": "error",
            }
        ],
        "execution_metadata": _execution_metadata(
            state,
            component_estimate_count=0,
        ),
        "trace_events": [
            {
                "event_type": "component_estimation_failed",
                "node": "generate_estimate",
                "summary": (
                    "Deterministic component estimation could not run."
                ),
                "evidence_refs": [],
                "state_delta_keys": [
                    "component_estimates",
                    "review_required",
                    "errors",
                    "execution_metadata",
                    "trace_events",
                ],
            }
        ],
    }


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


def build_generate_estimate_node(
    dependencies: GraphNodeDependencies,
) -> GenerateEstimateNode:
    """Create the deterministic component-estimation node."""

    async def generate_estimate(
        state: EstimationGraphState,
    ) -> EstimationGraphState:
        try:
            components = _validated_components(
                state.get("components")
            )
        except (AttributeError, KeyError, TypeError, ValueError):
            return _failure_update(
                state,
                code="missing_components",
                message=(
                    "No classified components are available "
                    "for deterministic estimation."
                ),
            )

        known_component_ids = {
            component["component_id"]
            for component in components
        }

        try:
            evidence = _validated_evidence(
                state.get("budget_matches", []),
                known_component_ids=known_component_ids,
            )
        except (AttributeError, KeyError, TypeError, ValueError):
            return _failure_update(
                state,
                code="invalid_budget_evidence",
                message=(
                    "Budget evidence is invalid or contains "
                    "duplicate provenance."
                ),
            )

        evidence_by_component = {
            component_id: [
                item
                for item in evidence
                if item.component_id == component_id
            ]
            for component_id in known_component_ids
        }

        estimates = [
            _component_estimate(
                component,
                evidence=evidence_by_component[
                    component["component_id"]
                ],
                policy=dependencies.estimation_policy,
            )
            for component in components
        ]

        issues = [
            issue
            for estimate in estimates
            if (issue := _issue_for_estimate(estimate)) is not None
        ]

        review_count = sum(
            estimate["grounding_status"] != "grounded"
            for estimate in estimates
        )

        if review_count:
            review_word = (
                "requires"
                if review_count == 1
                else "require"
            )
            event_type = (
                "component_estimates_generated_with_review"
            )
            summary = (
                f"Generated {len(estimates)} component estimates; "
                f"{review_count} {review_word} review."
            )
            state_delta_keys = [
                "component_estimates",
                "review_required",
                "errors",
                "execution_metadata",
                "trace_events",
            ]
        else:
            event_type = "component_estimates_generated"
            summary = (
                f"Generated {len(estimates)} grounded "
                "component estimates."
            )
            state_delta_keys = [
                "component_estimates",
                "execution_metadata",
                "trace_events",
            ]

        update: EstimationGraphState = {
            "component_estimates": estimates,
            "execution_metadata": _execution_metadata(
                state,
                component_estimate_count=len(estimates),
            ),
            "trace_events": [
                {
                    "event_type": event_type,
                    "node": "generate_estimate",
                    "summary": summary,
                    "evidence_refs": _evidence_refs(estimates),
                    "state_delta_keys": state_delta_keys,
                }
            ],
        }

        if review_count:
            update["review_required"] = True
            update["errors"] = issues

        return update

    return generate_estimate
