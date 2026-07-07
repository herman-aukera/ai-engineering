"""
Session 12 deterministic agent tools.

The agent loop may call these tools, but CI must be able to test them without
live provider calls.
"""

from __future__ import annotations

from app.generation.agentic.agent_schemas import (
    CalculateEstimateInput,
    CalculateEstimateOutput,
    EstimateComponentOutput,
    SearchBudgetsInput,
    SearchBudgetsOutput,
    ValidateEstimateInput,
    ValidateEstimateOutput,
)

_COMPLEXITY_DEFAULT_HOURS = {
    "low": 16.0,
    "medium": 40.0,
    "high": 80.0,
}


def calculate_estimate(payload: CalculateEstimateInput) -> CalculateEstimateOutput:
    """Calculate a deterministic estimate from component inputs."""

    components: list[EstimateComponentOutput] = []

    for component in payload.components:
        hours = component.reference_hours
        if hours is None:
            hours = _COMPLEXITY_DEFAULT_HOURS[component.complexity]

        cost = hours * payload.hourly_rate_eur
        components.append(
            EstimateComponentOutput(
                name=component.name,
                hours=round(hours, 2),
                cost_eur=round(cost, 2),
                rationale=(
                    f"Deterministic {component.complexity} complexity estimate"
                    " using reference hours when provided."
                ),
            )
        )

    subtotal_hours = round(sum(component.hours for component in components), 2)
    contingency_hours = round(subtotal_hours * payload.contingency_pct, 2)
    total_hours = round(subtotal_hours + contingency_hours, 2)

    return CalculateEstimateOutput(
        components=components,
        subtotal_hours=subtotal_hours,
        contingency_hours=contingency_hours,
        total_hours=total_hours,
        total_cost_eur=round(total_hours * payload.hourly_rate_eur, 2),
    )


def validate_estimate(payload: ValidateEstimateInput) -> ValidateEstimateOutput:
    """Validate deterministic estimate coherence before final answer."""

    errors: list[str] = []
    warnings: list[str] = []

    component_names = [component.name for component in payload.estimate.components]
    missing = [
        required_name
        for required_name in payload.required_component_names
        if required_name not in component_names
    ]
    if missing:
        errors.append(f"Missing required components: {', '.join(missing)}")

    component_hours = sum(component.hours for component in payload.estimate.components)
    if payload.estimate.subtotal_hours != round(component_hours, 2):
        errors.append("Subtotal hours does not match component hours.")

    if payload.estimate.total_hours < payload.estimate.subtotal_hours:
        errors.append("Total hours cannot be lower than subtotal hours.")

    if payload.estimate.contingency_hours == 0:
        warnings.append("No contingency was applied.")

    return ValidateEstimateOutput(valid=not errors, warnings=warnings, errors=errors)


def search_budgets(payload: SearchBudgetsInput) -> SearchBudgetsOutput:
    """
    Temporary deterministic search_budgets shell.

    Slice 7 will replace this shell with the real Session 9-10 retrieval wrapper.
    """

    return SearchBudgetsOutput(query=payload.query, hits=[])
