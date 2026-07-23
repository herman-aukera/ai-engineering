"""Provider-neutral contracts for bounded agent tool execution."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

AgentRunStatus = Literal[
    "completed",
    "iteration_limit",
    "tool_call_limit",
    "latency_budget_exhausted",
    "cost_budget_exhausted",
    "output_limit_exceeded",
    "provider_error",
]
AgentEventKind = Literal[
    "model_turn",
    "tool_executed",
    "tool_rejected",
    "runtime_stopped",
]


class StrictAgentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentToolSpec(StrictAgentModel):
    """One allow-listed function definition exposed to an agent model."""

    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    description: str = Field(min_length=5, max_length=2000)
    parameters: dict[str, Any]


class AgentToolCall(StrictAgentModel):
    """Normalized provider tool request with parsed JSON arguments."""

    call_id: str = Field(min_length=1, max_length=240)
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    arguments: dict[str, Any]


class AgentModelTurn(StrictAgentModel):
    """One provider-neutral model turn."""

    content: str | None = None
    tool_calls: list[AgentToolCall] = Field(default_factory=list)
    provider: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=240)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0)
    finish_reason: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_visible_output(self) -> AgentModelTurn:
        if not (self.content or "").strip() and not self.tool_calls:
            raise ValueError("model turn must contain visible content or tool calls")
        return self


class AgentToolObservation(StrictAgentModel):
    """Safe result returned to the model and retained for audit."""

    call_id: str
    tool_name: str
    ok: bool
    output: Any = None
    error_code: str | None = None
    error_message: str | None = None


class AgentRuntimeLimits(StrictAgentModel):
    """Hard execution budgets enforced by Python rather than model prose."""

    max_iterations: int = Field(default=8, ge=1, le=100)
    max_tool_calls: int = Field(default=12, ge=0, le=500)
    max_elapsed_ms: int = Field(default=120_000, ge=1)
    max_cost_usd: float = Field(default=1.0, ge=0)
    max_model_output_chars: int = Field(default=12_000, ge=1)
    max_tool_output_chars: int = Field(default=8_000, ge=1)


class AgentRuntimeEvent(StrictAgentModel):
    """Concise domain event without raw prompts or hidden reasoning."""

    sequence: int = Field(ge=1)
    kind: AgentEventKind
    summary: str = Field(min_length=1, max_length=2000)
    iteration: int = Field(ge=0)
    tool_name: str | None = None
    call_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentRuntimeResult(StrictAgentModel):
    """Terminal bounded-agent result safe for checkpointing."""

    status: AgentRunStatus
    final_text: str | None = None
    provider: str | None = None
    model: str | None = None
    iterations: int = Field(ge=0)
    tool_call_count: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_usd: float = Field(ge=0)
    elapsed_ms: int = Field(ge=0)
    observations: list[AgentToolObservation] = Field(default_factory=list)
    events: list[AgentRuntimeEvent] = Field(default_factory=list)
