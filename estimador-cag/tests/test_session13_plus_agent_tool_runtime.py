from __future__ import annotations

import asyncio
from collections.abc import Sequence

import pytest
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.agent_runtime import (
    AgentModelTurn,
    AgentRuntimeLimits,
    AgentToolCall,
    AgentToolSpec,
)
from app.services.agent_tool_runtime import (
    RegisteredAgentTool,
    run_bounded_agent,
)


class EchoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=100)


class ScriptedModel:
    def __init__(self, turns: Sequence[AgentModelTurn]) -> None:
        self.turns = list(turns)
        self.messages_seen: list[list[dict]] = []
        self.tools_seen: list[list[AgentToolSpec]] = []

    async def complete_turn(self, *, messages, tools) -> AgentModelTurn:
        self.messages_seen.append([dict(message) for message in messages])
        self.tools_seen.append(list(tools))
        if not self.turns:
            raise RuntimeError("scripted model exhausted")
        return self.turns.pop(0)


class SlowModel:
    async def complete_turn(self, *, messages, tools) -> AgentModelTurn:
        await asyncio.sleep(0.05)
        return _turn(content="late")


def _turn(
    *,
    content: str | None = None,
    calls: list[AgentToolCall] | None = None,
    cost_usd: float = 0.0,
) -> AgentModelTurn:
    return AgentModelTurn(
        content=content,
        tool_calls=calls or [],
        provider="fake",
        model="fake-agent-v1",
        input_tokens=10,
        output_tokens=5,
        cost_usd=cost_usd,
        finish_reason="tool_calls" if calls else "stop",
    )


def _call(call_id: str, *, text: str = "hello", name: str = "echo") -> AgentToolCall:
    return AgentToolCall(
        call_id=call_id,
        name=name,
        arguments={"text": text},
    )


def _tool(handler) -> RegisteredAgentTool:
    return RegisteredAgentTool(
        spec=AgentToolSpec(
            name="echo",
            description="Return the validated text for deterministic testing.",
            parameters=EchoArgs.model_json_schema(),
        ),
        arguments_model=EchoArgs,
        handler=handler,
    )


@pytest.mark.asyncio
async def test_agent_executes_tool_then_returns_natural_final_text() -> None:
    executed: list[str] = []

    async def echo(arguments: BaseModel):
        typed = EchoArgs.model_validate(arguments)
        executed.append(typed.text)
        return {"echo": typed.text}

    model = ScriptedModel(
        [
            _turn(calls=[_call("call-1")]),
            _turn(content="Recovered estimate is ready."),
        ]
    )

    result = await run_bounded_agent(
        model_port=model,
        system_prompt="Use allow-listed tools and stop when complete.",
        user_prompt="Recover one missing estimate.",
        tools=[_tool(echo)],
    )

    assert result.status == "completed"
    assert result.final_text == "Recovered estimate is ready."
    assert result.iterations == 2
    assert result.tool_call_count == 1
    assert executed == ["hello"]
    assert result.observations[0].ok is True
    assert result.observations[0].output == {"echo": "hello"}
    second_messages = model.messages_seen[1]
    assert second_messages[-2]["role"] == "assistant"
    assert second_messages[-1]["role"] == "tool"
    assert second_messages[-1]["tool_call_id"] == "call-1"


@pytest.mark.asyncio
async def test_duplicate_semantic_tool_call_is_not_executed_twice() -> None:
    calls = 0

    def echo(arguments: BaseModel):
        nonlocal calls
        calls += 1
        return {"echo": EchoArgs.model_validate(arguments).text}

    model = ScriptedModel(
        [
            _turn(calls=[_call("call-1"), _call("call-2")]),
            _turn(content="Done after duplicate protection."),
        ]
    )

    result = await run_bounded_agent(
        model_port=model,
        system_prompt="Use tools.",
        user_prompt="Test duplicate protection.",
        tools=[_tool(echo)],
    )

    assert result.status == "completed"
    assert result.tool_call_count == 2
    assert calls == 1
    assert [observation.ok for observation in result.observations] == [True, False]
    assert result.observations[1].error_code == "duplicate_tool_call"


@pytest.mark.asyncio
async def test_unknown_tool_is_rejected_by_allow_list() -> None:
    model = ScriptedModel(
        [
            _turn(calls=[_call("call-unknown", name="delete_repository")]),
            _turn(content="Stopped after safe rejection."),
        ]
    )

    result = await run_bounded_agent(
        model_port=model,
        system_prompt="Use tools.",
        user_prompt="Attempt an unknown tool.",
        tools=[_tool(lambda arguments: {"unexpected": True})],
    )

    assert result.status == "completed"
    assert result.observations[0].ok is False
    assert result.observations[0].error_code == "tool_not_allowed"


@pytest.mark.asyncio
async def test_invalid_tool_arguments_return_safe_observation() -> None:
    model = ScriptedModel(
        [
            _turn(
                calls=[
                    AgentToolCall(
                        call_id="call-invalid",
                        name="echo",
                        arguments={"text": ""},
                    )
                ]
            ),
            _turn(content="Handled validation failure."),
        ]
    )

    result = await run_bounded_agent(
        model_port=model,
        system_prompt="Use tools.",
        user_prompt="Test argument validation.",
        tools=[_tool(lambda arguments: {"unexpected": True})],
    )

    assert result.status == "completed"
    assert result.observations[0].error_code == "invalid_tool_arguments"


@pytest.mark.asyncio
async def test_tool_call_budget_stops_before_execution() -> None:
    executed = False

    def echo(arguments: BaseModel):
        nonlocal executed
        executed = True
        return {"echo": "unexpected"}

    result = await run_bounded_agent(
        model_port=ScriptedModel([_turn(calls=[_call("call-1")])]),
        system_prompt="Use tools.",
        user_prompt="Exhaust tool budget.",
        tools=[_tool(echo)],
        limits=AgentRuntimeLimits(max_tool_calls=0),
    )

    assert result.status == "tool_call_limit"
    assert result.tool_call_count == 0
    assert executed is False


@pytest.mark.asyncio
async def test_cost_budget_stops_before_tools_execute() -> None:
    result = await run_bounded_agent(
        model_port=ScriptedModel(
            [_turn(calls=[_call("call-1")], cost_usd=0.2)]
        ),
        system_prompt="Use tools.",
        user_prompt="Exhaust cost budget.",
        tools=[_tool(lambda arguments: {"unexpected": True})],
        limits=AgentRuntimeLimits(max_cost_usd=0.1),
    )

    assert result.status == "cost_budget_exhausted"
    assert result.cost_usd == 0.2
    assert result.tool_call_count == 0


@pytest.mark.asyncio
async def test_visible_output_limit_is_enforced() -> None:
    result = await run_bounded_agent(
        model_port=ScriptedModel([_turn(content="too long")]),
        system_prompt="Answer.",
        user_prompt="Exhaust output budget.",
        tools=[],
        limits=AgentRuntimeLimits(max_model_output_chars=3),
    )

    assert result.status == "output_limit_exceeded"
    assert result.final_text is None


@pytest.mark.asyncio
async def test_latency_budget_times_out_provider() -> None:
    result = await run_bounded_agent(
        model_port=SlowModel(),
        system_prompt="Answer.",
        user_prompt="Exhaust latency budget.",
        tools=[],
        limits=AgentRuntimeLimits(max_elapsed_ms=1),
    )

    assert result.status == "latency_budget_exhausted"


@pytest.mark.asyncio
async def test_iteration_budget_stops_repeated_distinct_calls() -> None:
    model = ScriptedModel(
        [
            _turn(calls=[_call("call-1", text="one")]),
            _turn(calls=[_call("call-2", text="two")]),
        ]
    )

    result = await run_bounded_agent(
        model_port=model,
        system_prompt="Use tools.",
        user_prompt="Exhaust iteration budget.",
        tools=[_tool(lambda arguments: {"ok": True})],
        limits=AgentRuntimeLimits(max_iterations=2),
    )

    assert result.status == "iteration_limit"
    assert result.iterations == 2
    assert result.tool_call_count == 2
