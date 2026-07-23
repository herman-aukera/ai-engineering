"""
Session 12 agent schemas.

These models define the deterministic trace and tool contracts used by the
hand-written reason-act-observe loop.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

TraceRole = Literal["reasoning", "function_call", "function_call_output", "final"]
ToolName = Literal["search_budgets", "calculate_estimate", "validate_estimate"]


class AgentTraceItem(BaseModel):
    """One readable item in the manual agent loop trace."""

    role: TraceRole
    content: str
    tool_name: ToolName | None = None
    call_id: str | None = None
    arguments: dict[str, Any] | None = None
    output: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_tool_trace_contract(self) -> AgentTraceItem:
        if self.role == "function_call":
            if not self.tool_name:
                raise ValueError("function_call trace items require tool_name")
            if not self.call_id:
                raise ValueError("function_call trace items require call_id")
            if self.arguments is None:
                raise ValueError("function_call trace items require arguments")

        if self.role == "function_call_output":
            if not self.call_id:
                raise ValueError("function_call_output trace items require call_id")
            if self.output is None:
                raise ValueError("function_call_output trace items require output")

        return self


class SearchBudgetsInput(BaseModel):
    """Strict input for the search_budgets tool."""

    query: str = Field(min_length=3, max_length=500)
    filters: dict[str, str | int | float | bool] | None = None


class BudgetSearchHit(BaseModel):
    """One retrieved budget/component hit exposed to the agent."""

    budget_id: str = Field(min_length=1)
    component_id: str | None = None
    title: str = Field(min_length=1)
    snippet: str = Field(min_length=1)
    score: float = Field(ge=0)


class SearchBudgetsOutput(BaseModel):
    """Strict output for the search_budgets tool."""

    query: str
    hits: list[BudgetSearchHit]


class EstimateComponentInput(BaseModel):
    """One component to estimate deterministically."""

    name: str = Field(min_length=2, max_length=160)
    complexity: Literal["low", "medium", "high"] = "medium"
    reference_hours: float | None = Field(default=None, ge=0, le=10000)


class CalculateEstimateInput(BaseModel):
    """Strict input for the calculate_estimate tool."""

    components: list[EstimateComponentInput] = Field(min_length=1)
    hourly_rate_eur: float = Field(default=60.0, gt=0, le=1000)
    contingency_pct: float = Field(default=0.15, ge=0, le=1)


class EstimateComponentOutput(BaseModel):
    """One deterministic estimated component."""

    name: str
    hours: float = Field(ge=0)
    cost_eur: float = Field(ge=0)
    rationale: str


class CalculateEstimateOutput(BaseModel):
    """Strict output for the calculate_estimate tool."""

    components: list[EstimateComponentOutput]
    subtotal_hours: float = Field(ge=0)
    contingency_hours: float = Field(ge=0)
    total_hours: float = Field(ge=0)
    total_cost_eur: float = Field(ge=0)


class ValidateEstimateInput(BaseModel):
    """Strict input for deterministic estimate guardrails."""

    estimate: CalculateEstimateOutput
    required_component_names: list[str] = Field(default_factory=list)


class ValidateEstimateOutput(BaseModel):
    """Strict output for deterministic estimate guardrails."""

    valid: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class AgentRunRequest(BaseModel):
    """Input for a Session 12 agent run."""

    transcript: str = Field(min_length=20)
    max_iterations: int = Field(default=8, ge=1, le=20)
    provider: Literal["fake", "deepseek", "kimi", "openai"] = "fake"
    model: str | None = None


class AgentRunResult(BaseModel):
    """Final Session 12 agent result."""

    estimate: CalculateEstimateOutput
    validation: ValidateEstimateOutput | None = None
    trace: list[AgentTraceItem]
    provider: str
    model: str | None = None
    terminated: bool = True
