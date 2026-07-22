"""Deterministic contracts for the OpenAI Responses tool adapter."""

from __future__ import annotations

from types import SimpleNamespace

from app.schemas.agent_runtime import AgentToolSpec
from app.schemas.v5_provider_selection import ProviderSelection
from app.services.openai_responses_agent import (
    _input_items,
    _tool_calls,
    _usage,
)
from app.services.provider_readiness import StageRoutingPolicy


def _tool_spec() -> AgentToolSpec:
    return AgentToolSpec(
        name="record_value",
        description="Record one exact benchmark value.",
        parameters={
            "type": "object",
            "properties": {
                "value": {"type": "integer"},
                "label": {"type": "string"},
            },
            "required": ["value", "label"],
            "additionalProperties": False,
        },
    )


def test_input_items_preserve_function_call_and_tool_output_protocol() -> None:
    instructions, items = _input_items(
        [
            {"role": "system", "content": "Use the tool exactly once."},
            {"role": "user", "content": "Record seven."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {
                            "name": "record_value",
                            "arguments": '{"label":"seven","value":7}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call-1",
                "name": "record_value",
                "content": '{"ok":true}',
            },
        ]
    )
    assert instructions == "Use the tool exactly once."
    assert items == [
        {"role": "user", "content": "Record seven."},
        {
            "type": "function_call",
            "call_id": "call-1",
            "name": "record_value",
            "arguments": '{"label":"seven","value":7}',
        },
        {
            "type": "function_call_output",
            "call_id": "call-1",
            "output": '{"ok":true}',
        },
    ]


def test_response_function_call_is_normalized_to_agent_contract() -> None:
    response = SimpleNamespace(
        output=[
            SimpleNamespace(
                type="reasoning",
            ),
            SimpleNamespace(
                type="function_call",
                id="item-1",
                call_id="call-1",
                name="record_value",
                arguments='{"value":7,"label":"seven"}',
            ),
        ]
    )
    calls = _tool_calls(response)
    assert len(calls) == 1
    assert calls[0].call_id == "call-1"
    assert calls[0].name == "record_value"
    assert calls[0].arguments == {"value": 7, "label": "seven"}


def test_invalid_response_function_arguments_are_not_executed() -> None:
    response = SimpleNamespace(
        output=[
            SimpleNamespace(
                type="function_call",
                id="item-1",
                call_id="call-1",
                name="record_value",
                arguments="not-json",
            )
        ]
    )
    assert _tool_calls(response) == []


def test_responses_usage_is_normalized() -> None:
    response = SimpleNamespace(
        usage=SimpleNamespace(input_tokens=123, output_tokens=45)
    )
    assert _usage(response) == (123, 45)


def test_openai_product_intents_map_to_native_efforts() -> None:
    policy = StageRoutingPolicy()
    minimal = policy.resolve(
        stage="selective_recovery",
        selection=ProviderSelection(provider="openai", reasoning="minimal"),
        complexity_level="C2",
    )
    medium = policy.resolve(
        stage="selective_recovery",
        selection=ProviderSelection(provider="openai", reasoning="medium"),
        complexity_level="C3",
    )
    maximum = policy.resolve(
        stage="selective_recovery",
        selection=ProviderSelection(provider="openai", reasoning="max"),
        complexity_level="C5",
    )
    assert minimal.effort == "low"
    assert medium.effort == "medium"
    assert maximum.effort == "xhigh"
    assert maximum.model == "gpt-5.6-sol"


def test_tool_schema_is_strict_and_provider_neutral() -> None:
    tool = _tool_spec()
    assert tool.name == "record_value"
    assert tool.parameters["additionalProperties"] is False
