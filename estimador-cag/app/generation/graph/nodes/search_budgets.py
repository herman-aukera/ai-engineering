"""Third required Session 13 graph node: grounded budget retrieval."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from copy import deepcopy
from math import isfinite

from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.state import (
    BudgetMatch,
    ComponentItem,
    EstimationGraphState,
    IssueSeverity,
)

SearchBudgetsNode = Callable[
    [EstimationGraphState],
    Awaitable[EstimationGraphState],
]


def _execution_metadata(
    state: EstimationGraphState,
    *,
    budget_match_count: int,
) -> dict[str, str | int]:
    metadata: dict[str, str | int] = dict(
        state.get("execution_metadata", {})
    )
    metadata["budget_match_count"] = budget_match_count
    return metadata


def _existing_match_count(
    state: EstimationGraphState,
) -> int:
    existing = state.get("budget_matches", [])
    return len(existing) if isinstance(existing, list) else 0


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


def _normalize_optional_float(
    value: object,
    *,
    field_name: str,
    minimum: float | None = None,
    strictly_positive: bool = False,
) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")

    normalized = float(value)

    if not isfinite(normalized):
        raise ValueError(f"{field_name} must be finite")

    if strictly_positive and normalized <= 0:
        raise ValueError(f"{field_name} must be positive")

    if minimum is not None and normalized < minimum:
        raise ValueError(
            f"{field_name} must be at least {minimum}"
        )

    return normalized


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

        if component_id in seen_ids:
            raise ValueError("component_id must be unique")

        seen_ids.add(component_id)

        component = deepcopy(dict(raw_component))
        component["component_id"] = component_id
        components.append(component)

    return components


def _normalize_matches(
    raw_matches: object,
    *,
    expected_component_id: str,
) -> list[BudgetMatch]:
    if not isinstance(raw_matches, list):
        raise ValueError("budget matches must be a list")

    normalized: list[BudgetMatch] = []
    seen_provenance: set[tuple[str, str | None, str, str]] = set()

    for raw_match in raw_matches:
        if not isinstance(raw_match, Mapping):
            raise ValueError("budget match must be a mapping")

        component_id = _normalize_identifier(
            raw_match.get("component_id"),
            field_name="component_id",
        )

        if component_id != expected_component_id:
            raise ValueError(
                "budget match component_id does not match searched component"
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
        recorded_hours = _normalize_optional_float(
            raw_match.get("recorded_hours"),
            field_name="recorded_hours",
            strictly_positive=True,
        )
        distance = _normalize_optional_float(
            raw_match.get("distance"),
            field_name="distance",
            minimum=0.0,
        )
        score = _normalize_optional_float(
            raw_match.get("score"),
            field_name="score",
        )

        retrieval_method_value = raw_match.get("retrieval_method")
        if not isinstance(retrieval_method_value, str):
            raise ValueError("retrieval_method must be a string")

        retrieval_method = retrieval_method_value.strip()
        if not retrieval_method:
            raise ValueError("retrieval_method must not be blank")

        provenance_key = (
            budget_id,
            reference_component_id,
            source_document_id,
            source_chunk_id,
        )

        if provenance_key in seen_provenance:
            raise ValueError(
                "budget match provenance must be unique per component"
            )

        seen_provenance.add(provenance_key)

        normalized.append(
            {
                "component_id": component_id,
                "budget_id": budget_id,
                "reference_component_id": reference_component_id,
                "source_document_id": source_document_id,
                "source_chunk_id": source_chunk_id,
                "recorded_hours": recorded_hours,
                "distance": distance,
                "score": score,
                "retrieval_method": retrieval_method,
            }
        )

    return normalized


def _failure_update(
    state: EstimationGraphState,
    *,
    code: str,
    message: str,
    event_type: str,
    summary: str,
    severity: IssueSeverity,
) -> EstimationGraphState:
    existing_count = _existing_match_count(state)

    return {
        "budget_matches": [],
        "review_required": True,
        "errors": [
            {
                "code": code,
                "message": message,
                "node": "search_budgets",
                "severity": severity,
            }
        ],
        "execution_metadata": _execution_metadata(
            state,
            budget_match_count=existing_count,
        ),
        "trace_events": [
            {
                "event_type": event_type,
                "node": "search_budgets",
                "summary": summary,
                "evidence_refs": [],
                "state_delta_keys": [
                    "budget_matches",
                    "review_required",
                    "errors",
                    "execution_metadata",
                    "trace_events",
                ],
            }
        ],
    }


def _plural(
    count: int,
    *,
    singular: str,
    plural: str,
) -> str:
    return singular if count == 1 else plural


def _evidence_refs(
    components: Sequence[ComponentItem],
    matches: Sequence[BudgetMatch],
) -> list[str]:
    values = [
        *[
            component["component_id"]
            for component in components
        ],
        *[
            match["budget_id"]
            for match in matches
        ],
        *[
            (
                f"{match['source_document_id']}:"
                f"{match['source_chunk_id']}"
            )
            for match in matches
        ],
    ]
    return list(dict.fromkeys(values))


def build_search_budgets_node(
    dependencies: GraphNodeDependencies,
) -> SearchBudgetsNode:
    """Bind injected retrieval to the budget-search graph node."""

    async def search_budgets(
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
                    "for budget search."
                ),
                event_type="components_unavailable",
                summary="Budget search could not start.",
                severity="error",
            )

        new_matches: list[BudgetMatch] = []
        missing_component_ids: list[str] = []
        invalid_component_ids: list[str] = []

        for component in components:
            component_id = component["component_id"]

            raw_matches = (
                await dependencies.budget_searcher.search_budgets(
                    component=deepcopy(component),
                    k=dependencies.search_k,
                )
            )

            if not raw_matches:
                missing_component_ids.append(component_id)
                continue

            try:
                component_matches = _normalize_matches(
                    raw_matches,
                    expected_component_id=component_id,
                )
            except (
                AttributeError,
                KeyError,
                TypeError,
                ValueError,
            ):
                invalid_component_ids.append(component_id)
                continue

            if not component_matches:
                missing_component_ids.append(component_id)
                continue

            new_matches.extend(component_matches)

        errors = []

        if invalid_component_ids:
            joined_ids = ", ".join(invalid_component_ids)
            errors.append(
                {
                    "code": "invalid_budget_matches",
                    "message": (
                        "Budget search returned invalid provenance "
                        f"for components: {joined_ids}."
                    ),
                    "node": "search_budgets",
                    "severity": "error",
                }
            )

        if missing_component_ids:
            joined_ids = ", ".join(missing_component_ids)
            errors.append(
                {
                    "code": "missing_budget_matches",
                    "message": (
                        "No budget references were found "
                        f"for components: {joined_ids}."
                    ),
                    "node": "search_budgets",
                    "severity": "warning",
                }
            )

        existing_count = _existing_match_count(state)
        total_match_count = existing_count + len(new_matches)
        component_count = len(components)
        gap_count = (
            len(invalid_component_ids)
            + len(missing_component_ids)
        )

        match_word = _plural(
            len(new_matches),
            singular="match",
            plural="matches",
        )
        component_word = _plural(
            component_count,
            singular="component",
            plural="components",
        )

        if gap_count:
            gap_word = _plural(
                gap_count,
                singular="gap",
                plural="gaps",
            )
            event_type = "budget_matches_retrieved_with_gaps"
            summary = (
                f"Retrieved {len(new_matches)} budget {match_word} "
                f"for {component_count} {component_word} with "
                f"{gap_count} evidence {gap_word}."
            )
            state_delta_keys = [
                "budget_matches",
                "review_required",
                "errors",
                "execution_metadata",
                "trace_events",
            ]
        else:
            event_type = "budget_matches_retrieved"
            summary = (
                f"Retrieved {len(new_matches)} budget {match_word} "
                f"for {component_count} {component_word}."
            )
            state_delta_keys = [
                "budget_matches",
                "execution_metadata",
                "trace_events",
            ]

        update: EstimationGraphState = {
            # Reducer invariant: return only the newly retrieved items.
            "budget_matches": new_matches,
            "execution_metadata": _execution_metadata(
                state,
                budget_match_count=total_match_count,
            ),
            "trace_events": [
                {
                    "event_type": event_type,
                    "node": "search_budgets",
                    "summary": summary,
                    "evidence_refs": _evidence_refs(
                        components,
                        new_matches,
                    ),
                    "state_delta_keys": state_delta_keys,
                }
            ],
        }

        if errors:
            update["review_required"] = True
            update["errors"] = errors

        return update

    return search_budgets
