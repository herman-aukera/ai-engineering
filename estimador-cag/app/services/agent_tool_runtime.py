"""Bounded provider-neutral reason→tool→observation runtime."""

from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from app.schemas.agent_runtime import (
    AgentModelTurn,
    AgentRunStatus,
    AgentRuntimeEvent,
    AgentRuntimeLimits,
    AgentRuntimeResult,
    AgentToolCall,
    AgentToolObservation,
    AgentToolSpec,
)

AgentMessage = dict[str, Any]
AgentToolHandler = Callable[[BaseModel], Any | Awaitable[Any]]


class AgentModelPort(Protocol):
    """Provider-neutral model boundary used by the bounded runtime."""

    async def complete_turn(
        self,
        *,
        messages: Sequence[AgentMessage],
        tools: Sequence[AgentToolSpec],
    ) -> AgentModelTurn:
        """Return visible content, tool calls, and normalized usage metadata."""


@dataclass(frozen=True)
class RegisteredAgentTool:
    """Allow-listed tool with strict arguments and an injected implementation."""

    spec: AgentToolSpec
    arguments_model: type[BaseModel]
    handler: AgentToolHandler

    def __post_init__(self) -> None:
        if self.spec.parameters != self.arguments_model.model_json_schema():
            raise ValueError(
                "tool parameters must equal the registered arguments model schema"
            )


class DuplicateAgentToolCallError(RuntimeError):
    """Raised internally when a model repeats an already executed semantic call."""


def _json_text(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("tool output must be JSON serializable") from exc


def _semantic_call_key(call: AgentToolCall) -> str:
    return f"{call.name}:{_json_text(call.arguments)}"


def _tool_message(observation: AgentToolObservation) -> AgentMessage:
    return {
        "role": "tool",
        "tool_call_id": observation.call_id,
        "name": observation.tool_name,
        "content": observation.model_dump_json(exclude_none=True),
    }


def _assistant_message(turn: AgentModelTurn) -> AgentMessage:
    message: AgentMessage = {
        "role": "assistant",
        "content": turn.content or "",
    }
    if turn.tool_calls:
        message["tool_calls"] = [
            {
                "id": call.call_id,
                "type": "function",
                "function": {
                    "name": call.name,
                    "arguments": _json_text(call.arguments),
                },
            }
            for call in turn.tool_calls
        ]
    return message


def _event(
    *,
    events: list[AgentRuntimeEvent],
    kind: str,
    summary: str,
    iteration: int,
    tool_name: str | None = None,
    call_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> None:
    events.append(
        AgentRuntimeEvent(
            sequence=len(events) + 1,
            kind=kind,
            summary=summary,
            iteration=iteration,
            tool_name=tool_name,
            call_id=call_id,
            metadata=dict(metadata or {}),
        )
    )


def _remaining_seconds(*, started_at: float, max_elapsed_ms: int) -> float:
    elapsed = perf_counter() - started_at
    return max(0.0, (max_elapsed_ms / 1000) - elapsed)


async def _invoke_tool(
    tool: RegisteredAgentTool,
    arguments: BaseModel,
    *,
    timeout_seconds: float,
) -> object:
    result = tool.handler(arguments)
    if inspect.isawaitable(result):
        return await asyncio.wait_for(result, timeout=timeout_seconds)
    return result


def _terminal_result(
    *,
    status: AgentRunStatus,
    final_text: str | None,
    provider: str | None,
    model: str | None,
    iterations: int,
    tool_call_count: int,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    started_at: float,
    observations: list[AgentToolObservation],
    events: list[AgentRuntimeEvent],
) -> AgentRuntimeResult:
    return AgentRuntimeResult(
        status=status,
        final_text=final_text,
        provider=provider,
        model=model,
        iterations=iterations,
        tool_call_count=tool_call_count,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=round(cost_usd, 8),
        elapsed_ms=max(0, int((perf_counter() - started_at) * 1000)),
        observations=observations,
        events=events,
    )


async def run_bounded_agent(
    *,
    model_port: AgentModelPort,
    system_prompt: str,
    user_prompt: str,
    tools: Sequence[RegisteredAgentTool],
    limits: AgentRuntimeLimits | None = None,
) -> AgentRuntimeResult:
    """Run one bounded tool loop without storing prompts or hidden reasoning."""

    resolved_limits = limits or AgentRuntimeLimits()
    tool_registry: dict[str, RegisteredAgentTool] = {}
    for tool in tools:
        if tool.spec.name in tool_registry:
            raise ValueError(f"duplicate registered tool: {tool.spec.name}")
        tool_registry[tool.spec.name] = tool

    messages: list[AgentMessage] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    observations: list[AgentToolObservation] = []
    events: list[AgentRuntimeEvent] = []
    seen_call_ids: set[str] = set()
    seen_semantic_calls: set[str] = set()
    started_at = perf_counter()
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost_usd = 0.0
    tool_call_count = 0
    provider: str | None = None
    model: str | None = None

    for iteration in range(1, resolved_limits.max_iterations + 1):
        remaining = _remaining_seconds(
            started_at=started_at,
            max_elapsed_ms=resolved_limits.max_elapsed_ms,
        )
        if remaining <= 0:
            _event(
                events=events,
                kind="runtime_stopped",
                summary="Latency budget was exhausted before the next model turn.",
                iteration=iteration - 1,
            )
            return _terminal_result(
                status="latency_budget_exhausted",
                final_text=None,
                provider=provider,
                model=model,
                iterations=iteration - 1,
                tool_call_count=tool_call_count,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                cost_usd=total_cost_usd,
                started_at=started_at,
                observations=observations,
                events=events,
            )

        try:
            turn = await asyncio.wait_for(
                model_port.complete_turn(
                    messages=tuple(messages),
                    tools=tuple(tool.spec for tool in tools),
                ),
                timeout=remaining,
            )
        except TimeoutError:
            _event(
                events=events,
                kind="runtime_stopped",
                summary="The provider exceeded the remaining latency budget.",
                iteration=iteration,
            )
            return _terminal_result(
                status="latency_budget_exhausted",
                final_text=None,
                provider=provider,
                model=model,
                iterations=iteration,
                tool_call_count=tool_call_count,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                cost_usd=total_cost_usd,
                started_at=started_at,
                observations=observations,
                events=events,
            )
        except Exception as exc:
            _event(
                events=events,
                kind="runtime_stopped",
                summary=f"Provider execution failed with {type(exc).__name__}.",
                iteration=iteration,
                metadata={"error_type": type(exc).__name__},
            )
            return _terminal_result(
                status="provider_error",
                final_text=None,
                provider=provider,
                model=model,
                iterations=iteration,
                tool_call_count=tool_call_count,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                cost_usd=total_cost_usd,
                started_at=started_at,
                observations=observations,
                events=events,
            )

        provider = turn.provider
        model = turn.model
        total_input_tokens += turn.input_tokens
        total_output_tokens += turn.output_tokens
        total_cost_usd += turn.cost_usd
        visible_chars = len(turn.content or "")
        _event(
            events=events,
            kind="model_turn",
            summary=(
                f"Model turn produced {len(turn.tool_calls)} tool call(s) and "
                f"{visible_chars} visible character(s)."
            ),
            iteration=iteration,
            metadata={
                "provider": turn.provider,
                "model": turn.model,
                "input_tokens": turn.input_tokens,
                "output_tokens": turn.output_tokens,
                "cost_usd": turn.cost_usd,
                "finish_reason": turn.finish_reason,
            },
        )

        if visible_chars > resolved_limits.max_model_output_chars:
            _event(
                events=events,
                kind="runtime_stopped",
                summary="Visible model output exceeded the configured character limit.",
                iteration=iteration,
            )
            return _terminal_result(
                status="output_limit_exceeded",
                final_text=None,
                provider=provider,
                model=model,
                iterations=iteration,
                tool_call_count=tool_call_count,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                cost_usd=total_cost_usd,
                started_at=started_at,
                observations=observations,
                events=events,
            )

        if total_cost_usd > resolved_limits.max_cost_usd:
            _event(
                events=events,
                kind="runtime_stopped",
                summary="Cumulative provider cost exceeded the configured budget.",
                iteration=iteration,
            )
            return _terminal_result(
                status="cost_budget_exhausted",
                final_text=None,
                provider=provider,
                model=model,
                iterations=iteration,
                tool_call_count=tool_call_count,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                cost_usd=total_cost_usd,
                started_at=started_at,
                observations=observations,
                events=events,
            )

        messages.append(_assistant_message(turn))
        if not turn.tool_calls:
            return _terminal_result(
                status="completed",
                final_text=(turn.content or "").strip() or None,
                provider=provider,
                model=model,
                iterations=iteration,
                tool_call_count=tool_call_count,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                cost_usd=total_cost_usd,
                started_at=started_at,
                observations=observations,
                events=events,
            )

        for call in turn.tool_calls:
            if tool_call_count >= resolved_limits.max_tool_calls:
                _event(
                    events=events,
                    kind="runtime_stopped",
                    summary="Tool-call budget was exhausted before executing the next call.",
                    iteration=iteration,
                    tool_name=call.name,
                    call_id=call.call_id,
                )
                return _terminal_result(
                    status="tool_call_limit",
                    final_text=None,
                    provider=provider,
                    model=model,
                    iterations=iteration,
                    tool_call_count=tool_call_count,
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                    cost_usd=total_cost_usd,
                    started_at=started_at,
                    observations=observations,
                    events=events,
                )

            tool_call_count += 1
            semantic_key = _semantic_call_key(call)
            duplicate = call.call_id in seen_call_ids or semantic_key in seen_semantic_calls
            if duplicate:
                observation = AgentToolObservation(
                    call_id=call.call_id,
                    tool_name=call.name,
                    ok=False,
                    error_code="duplicate_tool_call",
                    error_message="This tool call was already processed and was not executed again.",
                )
                observations.append(observation)
                messages.append(_tool_message(observation))
                _event(
                    events=events,
                    kind="tool_rejected",
                    summary="Duplicate tool call was rejected without execution.",
                    iteration=iteration,
                    tool_name=call.name,
                    call_id=call.call_id,
                    metadata={"error_code": "duplicate_tool_call"},
                )
                continue

            seen_call_ids.add(call.call_id)
            seen_semantic_calls.add(semantic_key)
            registered = tool_registry.get(call.name)
            if registered is None:
                observation = AgentToolObservation(
                    call_id=call.call_id,
                    tool_name=call.name,
                    ok=False,
                    error_code="tool_not_allowed",
                    error_message="The requested tool is not in the runtime allow-list.",
                )
                observations.append(observation)
                messages.append(_tool_message(observation))
                _event(
                    events=events,
                    kind="tool_rejected",
                    summary="Unknown tool was rejected by the allow-list.",
                    iteration=iteration,
                    tool_name=call.name,
                    call_id=call.call_id,
                    metadata={"error_code": "tool_not_allowed"},
                )
                continue

            try:
                validated_arguments = registered.arguments_model.model_validate(
                    call.arguments
                )
            except ValidationError as exc:
                observation = AgentToolObservation(
                    call_id=call.call_id,
                    tool_name=call.name,
                    ok=False,
                    error_code="invalid_tool_arguments",
                    error_message=str(exc)[:1000],
                )
                observations.append(observation)
                messages.append(_tool_message(observation))
                _event(
                    events=events,
                    kind="tool_rejected",
                    summary="Tool arguments failed strict schema validation.",
                    iteration=iteration,
                    tool_name=call.name,
                    call_id=call.call_id,
                    metadata={"error_code": "invalid_tool_arguments"},
                )
                continue

            remaining = _remaining_seconds(
                started_at=started_at,
                max_elapsed_ms=resolved_limits.max_elapsed_ms,
            )
            if remaining <= 0:
                return _terminal_result(
                    status="latency_budget_exhausted",
                    final_text=None,
                    provider=provider,
                    model=model,
                    iterations=iteration,
                    tool_call_count=tool_call_count,
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                    cost_usd=total_cost_usd,
                    started_at=started_at,
                    observations=observations,
                    events=events,
                )

            try:
                output = await _invoke_tool(
                    registered,
                    validated_arguments,
                    timeout_seconds=remaining,
                )
                output_text = _json_text(output)
                if len(output_text) > resolved_limits.max_tool_output_chars:
                    raise ValueError("tool output exceeded the configured character limit")
                observation = AgentToolObservation(
                    call_id=call.call_id,
                    tool_name=call.name,
                    ok=True,
                    output=output,
                )
                event_kind = "tool_executed"
                summary = "Allow-listed tool executed successfully."
                metadata = {"output_chars": len(output_text)}
            except Exception as exc:
                observation = AgentToolObservation(
                    call_id=call.call_id,
                    tool_name=call.name,
                    ok=False,
                    error_code="tool_execution_failed",
                    error_message=f"{type(exc).__name__}: {str(exc)[:800]}",
                )
                event_kind = "tool_rejected"
                summary = "Tool execution failed and a safe observation was returned."
                metadata = {
                    "error_code": "tool_execution_failed",
                    "error_type": type(exc).__name__,
                }

            observations.append(observation)
            messages.append(_tool_message(observation))
            _event(
                events=events,
                kind=event_kind,
                summary=summary,
                iteration=iteration,
                tool_name=call.name,
                call_id=call.call_id,
                metadata=metadata,
            )

    _event(
        events=events,
        kind="runtime_stopped",
        summary="Iteration budget was exhausted before a natural model stop.",
        iteration=resolved_limits.max_iterations,
    )
    return _terminal_result(
        status="iteration_limit",
        final_text=None,
        provider=provider,
        model=model,
        iterations=resolved_limits.max_iterations,
        tool_call_count=tool_call_count,
        input_tokens=total_input_tokens,
        output_tokens=total_output_tokens,
        cost_usd=total_cost_usd,
        started_at=started_at,
        observations=observations,
        events=events,
    )
