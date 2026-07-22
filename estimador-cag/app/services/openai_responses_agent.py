"""OpenAI Responses adapter for reasoning-enabled function tool turns."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from openai import AsyncOpenAI, OpenAI

from app.schemas.agent_runtime import AgentModelTurn, AgentToolCall, AgentToolSpec
from app.services.costs import estimate_cost_usd

_OPENAI_REQUEST_TIMEOUT_SECONDS = 60.0


def _function_tools(tools: Sequence[AgentToolSpec]) -> list[dict[str, object]]:
    return [
        {
            "type": "function",
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
            "strict": True,
        }
        for tool in tools
    ]


def _input_items(messages: Sequence[dict[str, Any]]) -> tuple[str | None, list[dict[str, object]]]:
    instructions: list[str] = []
    items: list[dict[str, object]] = []
    for message in messages:
        role = str(message.get("role", ""))
        content = message.get("content")
        if role == "system":
            if isinstance(content, str) and content:
                instructions.append(content)
            continue
        if role in {"user", "assistant"}:
            if isinstance(content, str) and content:
                items.append({"role": role, "content": content})
            tool_calls = message.get("tool_calls")
            if role == "assistant" and isinstance(tool_calls, list):
                for raw_call in tool_calls:
                    if not isinstance(raw_call, Mapping):
                        continue
                    function = raw_call.get("function")
                    if not isinstance(function, Mapping):
                        continue
                    call_id = raw_call.get("id")
                    name = function.get("name")
                    arguments = function.get("arguments")
                    if all(isinstance(value, str) and value for value in (call_id, name, arguments)):
                        items.append(
                            {
                                "type": "function_call",
                                "call_id": call_id,
                                "name": name,
                                "arguments": arguments,
                            }
                        )
            continue
        if role == "tool":
            call_id = message.get("tool_call_id")
            if isinstance(call_id, str) and call_id:
                items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": content if isinstance(content, str) else json.dumps(content),
                    }
                )
    return ("\n\n".join(instructions) or None), items


def _tool_calls(response: object) -> list[AgentToolCall]:
    output = getattr(response, "output", None)
    if not isinstance(output, list):
        return []
    calls: list[AgentToolCall] = []
    for item in output:
        if getattr(item, "type", None) != "function_call":
            continue
        name = getattr(item, "name", None)
        arguments = getattr(item, "arguments", None)
        call_id = getattr(item, "call_id", None) or getattr(item, "id", None)
        if not all(isinstance(value, str) and value for value in (name, arguments, call_id)):
            continue
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            calls.append(AgentToolCall(call_id=call_id, name=name, arguments=parsed))
    return calls


def _usage(response: object) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    input_tokens = getattr(usage, "input_tokens", 0) if usage is not None else 0
    output_tokens = getattr(usage, "output_tokens", 0) if usage is not None else 0
    return int(input_tokens or 0), int(output_tokens or 0)


async def complete_openai_responses_turn(
    *,
    api_key: str,
    base_url: str,
    model: str,
    effort: str,
    messages: Sequence[dict[str, Any]],
    tools: Sequence[AgentToolSpec],
    max_output_tokens: int,
) -> AgentModelTurn:
    """Execute one bounded OpenAI Responses turn with provider-native reasoning."""

    instructions, input_items = _input_items(messages)
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=_OPENAI_REQUEST_TIMEOUT_SECONDS,
        max_retries=1,
    )
    response = await client.responses.create(
        model=model,
        instructions=instructions,
        input=input_items,
        tools=_function_tools(tools),
        tool_choice="auto" if tools else "none",
        reasoning={"effort": effort},
        max_output_tokens=max_output_tokens,
        store=False,
    )
    input_tokens, output_tokens = _usage(response)
    cost = estimate_cost_usd(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    raw_cost = cost.get("cost_usd")
    normalized_cost = (
        max(0.0, float(raw_cost))
        if isinstance(raw_cost, int | float) and not isinstance(raw_cost, bool)
        else 0.0
    )
    return AgentModelTurn(
        content=(getattr(response, "output_text", None) or None),
        tool_calls=_tool_calls(response),
        provider="openai",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=normalized_cost,
        finish_reason=str(getattr(response, "status", "completed")),
    )


def benchmark_openai_tool_call(
    *,
    api_key: str,
    base_url: str,
    model: str,
    effort: str,
    instructions: str,
    user_input: str,
    tool: Mapping[str, object],
    max_output_tokens: int,
) -> object:
    """Synchronous Responses call used by the matched calibration runner."""

    function = tool.get("function")
    if not isinstance(function, Mapping):
        raise ValueError("benchmark tool must contain a function definition")
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=_OPENAI_REQUEST_TIMEOUT_SECONDS,
        max_retries=1,
    )
    return client.responses.create(
        model=model,
        instructions=instructions,
        input=user_input,
        tools=[
            {
                "type": "function",
                "name": function["name"],
                "description": function.get("description", ""),
                "parameters": function["parameters"],
                "strict": bool(function.get("strict", True)),
            }
        ],
        tool_choice="required",
        reasoning={"effort": effort},
        max_output_tokens=max_output_tokens,
        store=False,
    )


def benchmark_responses_tool_arguments(response: object) -> dict[str, Any] | None:
    """Return exact benchmark tool arguments from one Responses result."""

    calls = _tool_calls(response)
    if len(calls) != 1 or calls[0].name != "record_value":
        return None
    return calls[0].arguments
