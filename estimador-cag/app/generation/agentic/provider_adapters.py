"""
Session 12 provider adapter contracts.

Provider adapters normalize fake, DeepSeek, Kimi, and OpenAI planning behavior
into the same planned-step protocol before the deterministic agent loop executes
tools.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, model_validator

from app.generation.agentic.agent_schemas import EstimateComponentInput

AgentProviderName = Literal["fake", "deepseek", "kimi", "openai"]
PlannedStepKind = Literal["reasoning", "function_call", "final"]


class ProviderAdapterRequest(BaseModel):
    """Input sent to a provider adapter before tool execution."""

    transcript: str = Field(min_length=20)
    provider: AgentProviderName
    model: str | None = None


class AgentPlannedStep(BaseModel):
    """One normalized provider-planned step before tool execution."""

    kind: PlannedStepKind
    content: str
    tool_name: str | None = None
    call_id: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_function_call_contract(self) -> AgentPlannedStep:
        if self.kind == "function_call":
            if not self.tool_name:
                raise ValueError("function_call planned steps require tool_name")
            if not self.call_id:
                raise ValueError("function_call planned steps require call_id")
        return self


class ProviderAdapter(Protocol):
    """Protocol implemented by Session 12 planning adapters."""

    def plan(self, request: ProviderAdapterRequest) -> list[AgentPlannedStep]:
        """Return normalized planned steps."""


def _components_from_transcript(transcript: str) -> list[EstimateComponentInput]:
    """Extract deterministic fake components from transcript keywords."""

    lowered = transcript.lower()
    components: list[EstimateComponentInput] = []

    if "jwt" in lowered or "authentication" in lowered:
        components.append(
            EstimateComponentInput(
                name="JWT authentication",
                complexity="medium",
                reference_hours=40,
            )
        )

    if "audit" in lowered:
        components.append(
            EstimateComponentInput(
                name="Audit logging",
                complexity="low",
                reference_hours=24,
            )
        )

    if "dashboard" in lowered or "admin" in lowered:
        components.append(
            EstimateComponentInput(
                name="Admin dashboard",
                complexity="medium",
                reference_hours=56,
            )
        )

    if "csv" in lowered or "import" in lowered:
        components.append(
            EstimateComponentInput(
                name="CSV import",
                complexity="medium",
                reference_hours=32,
            )
        )

    if not components:
        components.append(
            EstimateComponentInput(
                name="General implementation",
                complexity="medium",
                reference_hours=40,
            )
        )

    return components


class FakeProviderAdapter:
    """Deterministic provider adapter used by CI and trace artifacts."""

    def plan(self, request: ProviderAdapterRequest) -> list[AgentPlannedStep]:
        components = _components_from_transcript(request.transcript)

        return [
            AgentPlannedStep(
                kind="reasoning",
                content="Identify likely components from the transcript before estimating.",
            ),
            AgentPlannedStep(
                kind="function_call",
                content="Call search_budgets.",
                tool_name="search_budgets",
                call_id="call_search_auth",
                arguments={"query": "JWT authentication financial backend"},
            ),
            AgentPlannedStep(
                kind="function_call",
                content="Call search_budgets.",
                tool_name="search_budgets",
                call_id="call_search_audit",
                arguments={"query": "audit logging admin dashboard CSV import"},
            ),
            AgentPlannedStep(
                kind="reasoning",
                content="Use retrieved budget context plus transcript components to calculate effort.",
            ),
            AgentPlannedStep(
                kind="function_call",
                content="Call calculate_estimate.",
                tool_name="calculate_estimate",
                call_id="call_calculate_estimate",
                arguments={
                    "components": [component.model_dump() for component in components],
                    "hourly_rate_eur": 75,
                    "contingency_pct": 0.2,
                },
            ),
            AgentPlannedStep(
                kind="function_call",
                content="Call validate_estimate.",
                tool_name="validate_estimate",
                call_id="call_validate_estimate",
                arguments={
                    "required_component_names": [component.name for component in components],
                },
            ),
            AgentPlannedStep(
                kind="final",
                content="Return the structured estimate and readable trace.",
            ),
        ]


def build_provider_adapter(provider: AgentProviderName) -> ProviderAdapter:
    """Build a provider adapter by name."""

    if provider == "fake":
        return FakeProviderAdapter()

    raise ValueError(f"Provider adapter for {provider} is not implemented yet")
