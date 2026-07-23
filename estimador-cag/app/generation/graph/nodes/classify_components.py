"""Second required Session 13 graph node: component classification."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from copy import deepcopy

from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.state import (
    ComponentItem,
    EstimationGraphState,
    IssueSeverity,
    RequirementItem,
)

ClassifyComponentsNode = Callable[
    [EstimationGraphState],
    Awaitable[EstimationGraphState],
]


def _execution_metadata(
    state: EstimationGraphState,
    *,
    component_count: int,
) -> dict[str, str | int]:
    metadata: dict[str, str | int] = dict(
        state.get("execution_metadata", {})
    )
    metadata["component_count"] = component_count
    return metadata


def _known_requirement_ids(
    requirements: Sequence[RequirementItem],
) -> set[str]:
    known_ids: set[str] = set()

    for requirement in requirements:
        requirement_id = requirement.get("requirement_id")

        if not isinstance(requirement_id, str):
            raise ValueError("requirement_id must be a string")

        requirement_id = requirement_id.strip()

        if not requirement_id:
            raise ValueError("requirement_id must not be blank")
        if requirement_id in known_ids:
            raise ValueError("requirement_id must be unique")

        known_ids.add(requirement_id)

    return known_ids


def _normalize_components(
    components: Sequence[ComponentItem],
    *,
    known_requirement_ids: set[str],
) -> list[ComponentItem]:
    normalized: list[ComponentItem] = []
    seen_component_ids: set[str] = set()

    for component in components:
        component_id = component.get("component_id")
        name = component.get("name")
        category = component.get("category")
        requirement_ids = component.get("requirement_ids")

        if not isinstance(component_id, str):
            raise ValueError("component_id must be a string")
        if not isinstance(name, str):
            raise ValueError("component name must be a string")
        if not isinstance(category, str):
            raise ValueError("component category must be a string")
        if not isinstance(requirement_ids, list):
            raise ValueError("requirement_ids must be a list")

        component_id = component_id.strip()
        name = name.strip()
        category = category.strip()

        if not component_id:
            raise ValueError("component_id must not be blank")
        if not name:
            raise ValueError("component name must not be blank")
        if not category:
            raise ValueError("component category must not be blank")
        if component_id in seen_component_ids:
            raise ValueError("component_id must be unique")
        if not requirement_ids:
            raise ValueError("component must reference at least one requirement")

        normalized_requirement_ids: list[str] = []
        seen_requirement_ids: set[str] = set()

        for requirement_id in requirement_ids:
            if not isinstance(requirement_id, str):
                raise ValueError("linked requirement_id must be a string")

            requirement_id = requirement_id.strip()

            if not requirement_id:
                raise ValueError("linked requirement_id must not be blank")
            if requirement_id in seen_requirement_ids:
                raise ValueError(
                    "linked requirement_id must be unique within a component"
                )
            if requirement_id not in known_requirement_ids:
                raise ValueError(
                    "component references an unknown requirement_id"
                )

            seen_requirement_ids.add(requirement_id)
            normalized_requirement_ids.append(requirement_id)

        seen_component_ids.add(component_id)
        normalized.append(
            {
                "component_id": component_id,
                "name": name,
                "category": category,
                "requirement_ids": normalized_requirement_ids,
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
    return {
        "components": [],
        "review_required": True,
        "errors": [
            {
                "code": code,
                "message": message,
                "node": "classify_components",
                "severity": severity,
            }
        ],
        "execution_metadata": _execution_metadata(
            state,
            component_count=0,
        ),
        "trace_events": [
            {
                "event_type": event_type,
                "node": "classify_components",
                "summary": summary,
                "evidence_refs": [],
                "state_delta_keys": [
                    "components",
                    "review_required",
                    "errors",
                    "execution_metadata",
                    "trace_events",
                ],
            }
        ],
    }


def _success_trace(
    components: Sequence[ComponentItem],
    *,
    unmapped_requirement_ids: list[str],
) -> dict[str, object]:
    component_ids = [
        component["component_id"]
        for component in components
    ]
    mapped_requirement_ids = sorted(
        {
            requirement_id
            for component in components
            for requirement_id in component["requirement_ids"]
        }
    )

    evidence_refs = [
        *component_ids,
        *mapped_requirement_ids,
        *unmapped_requirement_ids,
    ]

    if unmapped_requirement_ids:
        component_word = (
            "component"
            if len(components) == 1
            else "components"
        )
        requirement_word = (
            "requirement"
            if len(unmapped_requirement_ids) == 1
            else "requirements"
        )

        return {
            "event_type": "components_classified_with_gaps",
            "node": "classify_components",
            "summary": (
                f"Classified {len(components)} implementation "
                f"{component_word} with "
                f"{len(unmapped_requirement_ids)} unmapped "
                f"{requirement_word}."
            ),
            "evidence_refs": evidence_refs,
            "state_delta_keys": [
                "components",
                "review_required",
                "errors",
                "execution_metadata",
                "trace_events",
            ],
        }

    component_word = (
        "component"
        if len(components) == 1
        else "components"
    )

    return {
        "event_type": "components_classified",
        "node": "classify_components",
        "summary": (
            f"Classified {len(components)} implementation "
            f"{component_word}."
        ),
        "evidence_refs": evidence_refs,
        "state_delta_keys": [
            "components",
            "execution_metadata",
            "trace_events",
        ],
    }


def build_classify_components_node(
    dependencies: GraphNodeDependencies,
) -> ClassifyComponentsNode:
    """Bind injected services to the component-classification node."""

    async def classify_components(
        state: EstimationGraphState,
    ) -> EstimationGraphState:
        requirements = state.get("requirements")

        if not isinstance(requirements, list) or not requirements:
            return _failure_update(
                state,
                code="missing_requirements",
                message=(
                    "No structured requirements are available "
                    "for classification."
                ),
                event_type="requirements_unavailable",
                summary="Component classification could not start.",
                severity="error",
            )

        try:
            known_requirement_ids = _known_requirement_ids(
                requirements
            )
        except (AttributeError, KeyError, TypeError, ValueError):
            return _failure_update(
                state,
                code="invalid_requirements",
                message=(
                    "The graph contains invalid requirements "
                    "for component classification."
                ),
                event_type="requirements_invalid",
                summary=(
                    "Component classification received invalid requirements."
                ),
                severity="error",
            )

        raw_components = (
            await dependencies.component_classifier.classify_components(
                requirements=deepcopy(requirements)
            )
        )

        try:
            components = _normalize_components(
                raw_components,
                known_requirement_ids=known_requirement_ids,
            )
        except (AttributeError, KeyError, TypeError, ValueError):
            return _failure_update(
                state,
                code="invalid_components",
                message=(
                    "Component classification returned "
                    "an invalid structured result."
                ),
                event_type="components_invalid",
                summary=(
                    "Component classification failed structured validation."
                ),
                severity="error",
            )

        if not components:
            return _failure_update(
                state,
                code="no_components",
                message="No implementation components were classified.",
                event_type="components_missing",
                summary=(
                    "Component classification produced no components."
                ),
                severity="warning",
            )

        mapped_requirement_ids = {
            requirement_id
            for component in components
            for requirement_id in component["requirement_ids"]
        }
        unmapped_requirement_ids = sorted(
            known_requirement_ids - mapped_requirement_ids
        )

        update: EstimationGraphState = {
            "components": components,
            "execution_metadata": _execution_metadata(
                state,
                component_count=len(components),
            ),
            "trace_events": [
                _success_trace(
                    components,
                    unmapped_requirement_ids=unmapped_requirement_ids,
                )
            ],
        }

        if unmapped_requirement_ids:
            joined_requirement_ids = ", ".join(
                unmapped_requirement_ids
            )
            update["review_required"] = True
            update["errors"] = [
                {
                    "code": "unmapped_requirements",
                    "message": (
                        "Some requirements were not assigned "
                        f"to a component: {joined_requirement_ids}."
                    ),
                    "node": "classify_components",
                    "severity": "warning",
                }
            ]

        return update

    return classify_components
