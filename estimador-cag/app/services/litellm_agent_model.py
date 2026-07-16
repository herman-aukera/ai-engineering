"""LiteLLM adapter for the provider-neutral bounded agent runtime."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import litellm

from app.config import TierName
from app.schemas.agent_runtime import AgentModelTurn, AgentToolCall, AgentToolSpec
from app.services.costs import estimate_cost_usd
from app.services.litellm_provider import LiteLLMProvider


class AgentProviderContractError(RuntimeError):
    """Raised when a provider response cannot satisfy the normalized turn contract."""


def _value(container: object, name: str, default: object = None) -> object:
    if isinstance(container, Mapping):
        return container.get(name, default)
    return getattr(container, name, default)


def _first_choice(response: object) -> object:
    choices = _value(response, "choices", [])
    if not isinstance(choices, Sequence) or isinstance(choices, (str, bytes)) or not choices:
        raise AgentProviderContractError("provider response does not contain a first choice")
    return choices[0]


def _content(message: object) -> str | None:
    raw_content = _value(message, "content")
    if raw_content is None:
        return None
    if isinstance(raw_content, str):
        normalized = raw_content.strip()
        return normalized or None
    if isinstance(raw_content, (dict, list)):
        return json.dumps(raw_content, ensure_ascii=False, sort_keys=True)
    return str(raw_content)


def _tool_calls(message: object) -> list[AgentToolCall]:
    raw_calls = _value(message, "tool_calls", []) or []
    if not isinstance(raw_calls, Sequence) or isinstance(raw_calls, (str, bytes)):
        raise AgentProviderContractError("provider tool_calls must be a sequence")

    calls: list[AgentToolCall] = []
    for raw_call in raw_calls:
        function = _value(raw_call, "function")
        if function is None:
            raise AgentProviderContractError("provider tool call does not contain function data")
        call_id = _value(raw_call, "id")
        name = _value(function, "name")
        raw_arguments = _value(function, "arguments", {})
        if isinstance(raw_arguments, str):
            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError as exc:
                raise AgentProviderContractError(
                    "provider tool arguments are not valid JSON"
                ) from exc
        elif isinstance(raw_arguments, Mapping):
            arguments = dict(raw_arguments)
        else:
            raise AgentProviderContractError(
                "provider tool arguments must be a JSON object or encoded object"
            )
        if not isinstance(arguments, dict):
            raise AgentProviderContractError("provider tool arguments must decode to an object")
        calls.append(
            AgentToolCall(
                call_id=str(call_id or ""),
                name=str(name or ""),
                arguments=arguments,
            )
        )
    return calls


def _usage(response: object) -> tuple[int, int]:
    usage = _value(response, "usage", {}) or {}
    input_tokens = _value(usage, "prompt_tokens", 0)
    output_tokens = _value(usage, "completion_tokens", 0)
    try:
        return max(0, int(input_tokens or 0)), max(0, int(output_tokens or 0))
    except (TypeError, ValueError) as exc:
        raise AgentProviderContractError("provider usage counters must be numeric") from exc


def _tools_payload(tools: Sequence[AgentToolSpec]) -> list[dict[str, object]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "strict": True,
            },
        }
        for tool in tools
    ]


def _litellm_completion_model(*, provider: str, model: str) -> str:
    """Route custom OpenAI-compatible DeepSeek model ids through LiteLLM."""

    if provider == "deepseek" and "/" not in model:
        return f"openai/{model}"
    return model


@dataclass(frozen=True)
class LiteLLMAgentModel:
    """Execute one OpenAI-compatible tool turn through logical provider tiers."""

    tier: TierName
    max_tokens: int = 2000
    resolver: LiteLLMProvider = field(default_factory=LiteLLMProvider)

    def __post_init__(self) -> None:
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")

    async def complete_turn(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[AgentToolSpec],
    ) -> AgentModelTurn:
        resolved = self.resolver.resolve_model(self.tier)
        response = await litellm.acompletion(
            model=_litellm_completion_model(
                provider=resolved.provider,
                model=resolved.model,
            ),
            messages=list(messages),
            tools=_tools_payload(tools),
            tool_choice="auto" if tools else None,
            api_key=resolved.api_key,
            api_base=resolved.base_url,
            temperature=resolved.temperature,
            max_tokens=self.max_tokens,
        )
        choice = _first_choice(response)
        message = _value(choice, "message")
        if message is None:
            raise AgentProviderContractError("provider choice does not contain a message")
        input_tokens, output_tokens = _usage(response)
        cost = estimate_cost_usd(
            model=resolved.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        raw_cost = cost.get("cost_usd")
        normalized_cost = (
            max(0.0, float(raw_cost))
            if isinstance(raw_cost, (int, float)) and not isinstance(raw_cost, bool)
            else 0.0
        )
        finish_reason = _value(choice, "finish_reason")
        return AgentModelTurn(
            content=_content(message),
            tool_calls=_tool_calls(message),
            provider=resolved.provider,
            model=resolved.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=normalized_cost,
            finish_reason=(
                str(finish_reason) if finish_reason is not None else None
            ),
        )
