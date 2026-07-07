from pydantic import ValidationError

from app.generation.agentic.agent_schemas import (
    AgentTraceItem,
    CalculateEstimateInput,
    EstimateComponentInput,
    SearchBudgetsInput,
    ValidateEstimateInput,
)
from app.generation.agentic.agent_tools import calculate_estimate, search_budgets, validate_estimate


def test_search_budgets_schema_is_strict():
    payload = SearchBudgetsInput(query="JWT authentication financial backend")

    assert payload.query == "JWT authentication financial backend"
    assert payload.filters is None

    try:
        SearchBudgetsInput(query="no")
    except ValidationError:
        pass
    else:
        raise AssertionError("short queries must fail validation")


def test_calculate_estimate_schema_is_strict():
    payload = CalculateEstimateInput(
        components=[
            EstimateComponentInput(name="Authentication backend", complexity="medium"),
            EstimateComponentInput(name="Audit logging", complexity="low", reference_hours=12),
        ],
        hourly_rate_eur=75,
        contingency_pct=0.2,
    )

    result = calculate_estimate(payload)

    assert result.subtotal_hours == 52.0
    assert result.contingency_hours == 10.4
    assert result.total_hours == 62.4
    assert result.total_cost_eur == 4680.0
    assert [component.name for component in result.components] == [
        "Authentication backend",
        "Audit logging",
    ]


def test_validate_estimate_detects_missing_required_component():
    estimate = calculate_estimate(
        CalculateEstimateInput(
            components=[EstimateComponentInput(name="Authentication backend")]
        )
    )

    validation = validate_estimate(
        ValidateEstimateInput(
            estimate=estimate,
            required_component_names=["Authentication backend", "Audit logging"],
        )
    )

    assert validation.valid is False
    assert validation.errors == ["Missing required components: Audit logging"]


def test_agent_trace_requires_call_id_for_tool_calls():
    try:
        AgentTraceItem(
            role="function_call",
            content="Call calculate_estimate",
            tool_name="calculate_estimate",
            arguments={},
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("function_call without call_id must fail validation")


def test_search_budgets_shell_returns_empty_hits_until_retrieval_is_wrapped():
    result = search_budgets(SearchBudgetsInput(query="mobile app login"))

    assert result.query == "mobile app login"
    assert result.hits == []
