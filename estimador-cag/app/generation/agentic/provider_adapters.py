"""
Session 12 provider adapter contracts.

Provider adapters normalize fake, DeepSeek, Kimi, and OpenAI planning behavior
into the same planned-step protocol before the deterministic agent loop executes
tools.
"""

from __future__ import annotations

import json
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


class ChatCompletionsLike(Protocol):
    """Minimal OpenAI-compatible chat completions protocol."""

    def create(self, **kwargs: Any) -> Any:
        """Create a chat completion."""


class ChatLike(Protocol):
    """Minimal client.chat protocol."""

    completions: ChatCompletionsLike


class OpenAICompatibleClientLike(Protocol):
    """Minimal OpenAI-compatible client protocol."""

    chat: ChatLike


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


def build_agent_planning_system_prompt() -> str:
    """Return strict JSON-only planning instructions for live adapters."""

    return """
Return only JSON with this exact shape:
{
  "steps": [
    {
      "kind": "reasoning",
      "content": "short private-free reasoning summary"
    },
    {
      "kind": "function_call",
      "content": "Call search_budgets.",
      "tool_name": "search_budgets",
      "call_id": "stable_unique_call_id",
      "arguments": {"query": "search query"}
    },
    {
      "kind": "function_call",
      "content": "Call calculate_estimate.",
      "tool_name": "calculate_estimate",
      "call_id": "stable_unique_call_id",
      "arguments": {
        "components": [
          {"name": "Component name", "complexity": "low|medium|high", "reference_hours": 40}
        ],
        "hourly_rate_eur": 75,
        "contingency_pct": 0.2
      }
    },
    {
      "kind": "function_call",
      "content": "Call validate_estimate.",
      "tool_name": "validate_estimate",
      "call_id": "stable_unique_call_id",
      "arguments": {"required_component_names": ["Component name"]}
    },
    {
      "kind": "final",
      "content": "Return the structured estimate."
    }
  ]
}

Rules:
- Return only JSON. No Markdown.
- Use only these tool names: search_budgets, calculate_estimate, validate_estimate.
- Every function_call must include tool_name, call_id, and arguments.
- Include at least one calculate_estimate call and one validate_estimate call.
- Keep call_id values stable and unique.
""".strip()


def _strip_markdown_json_fence(raw_content: str) -> str:
    """Remove a single Markdown code fence wrapper if a provider adds one."""

    stripped = raw_content.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    return "\n".join(lines).strip()


def _load_provider_json_object(raw_content: str) -> dict:
    """Load the first JSON object from provider content.

    Some live providers obey the planning prompt semantically but append
    extra prose or formatting. For the smoke runner, the normalized first
    JSON object is the contract boundary; shape validation still happens
    after parsing.
    """

    candidate = _strip_markdown_json_fence(raw_content)

    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        first_object_index = candidate.find("{")
        if first_object_index < 0:
            raise ValueError("Provider plan is not valid JSON: no JSON object found")

        decoder = json.JSONDecoder()
        try:
            payload, _end_index = decoder.raw_decode(candidate[first_object_index:])
        except json.JSONDecodeError as exc:
            raise ValueError(f"Provider plan is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("Provider plan must be a JSON object")

    return payload


def parse_provider_plan_json(raw_content: str) -> list[AgentPlannedStep]:
    """Parse provider JSON into normalized planned steps."""

    payload = _load_provider_json_object(raw_content)

    raw_steps = payload.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError("Provider plan must include a non-empty steps list")

    return [AgentPlannedStep(**step) for step in raw_steps]


class OpenAICompatibleProviderAdapter:
    """Adapter for OpenAI-compatible chat completion providers."""

    def __init__(
        self,
        *,
        client: OpenAICompatibleClientLike,
        model: str,
        provider: AgentProviderName,
        temperature: float | None = 0,
    ) -> None:
        self.client = client
        self.model = model
        self.provider = provider
        self.temperature = temperature

    def plan(self, request: ProviderAdapterRequest) -> list[AgentPlannedStep]:
        completion_kwargs = {
            "model": request.model or self.model,
            "messages": [
                {
                    "role": "system",
                    "content": build_agent_planning_system_prompt(),
                },
                {
                    "role": "user",
                    "content": request.transcript,
                },
            ],
        }
        if self.temperature is not None:
            completion_kwargs["temperature"] = self.temperature

        completion = self.client.chat.completions.create(**completion_kwargs)
        content = completion.choices[0].message.content
        return parse_provider_plan_json(content)


def build_provider_adapter(provider: AgentProviderName) -> ProviderAdapter:
    """Build a provider adapter by name."""

    if provider == "fake":
        return FakeProviderAdapter()

    raise ValueError(f"Provider adapter for {provider} is not implemented yet")
