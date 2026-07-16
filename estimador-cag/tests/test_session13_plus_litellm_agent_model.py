from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.schemas.agent_runtime import AgentToolSpec
from app.services import litellm_agent_model as adapter_module
from app.services.litellm_agent_model import (
    AgentProviderContractError,
    LiteLLMAgentModel,
)
from app.services.litellm_provider import ResolvedModel


@dataclass
class FakeResolver:
    resolved: ResolvedModel

    def resolve_model(self, tier):
        assert tier == "flash"
        return self.resolved


def _adapter() -> LiteLLMAgentModel:
    return LiteLLMAgentModel(
        tier="flash",
        resolver=FakeResolver(
            ResolvedModel(
                tier="flash",
                provider="deepseek",
                model="deepseek-test",
                api_key="test-key",
                base_url="https://provider.invalid/v1",
                temperature=0.3,
            )
        ),
    )


def _tool() -> AgentToolSpec:
    return AgentToolSpec(
        name="search_budgets",
        description="Search historical budget evidence for one selected component.",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    )


@pytest.mark.asyncio
async def test_litellm_adapter_normalizes_tool_calls_and_usage(monkeypatch) -> None:
    captured = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        return {
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {
                                    "name": "search_budgets",
                                    "arguments": '{"query":"JWT authentication"}',
                                },
                            }
                        ],
                    },
                }
            ],
            "usage": {
                "prompt_tokens": 120,
                "completion_tokens": 30,
            },
        }

    monkeypatch.setattr(adapter_module.litellm, "acompletion", fake_acompletion)

    turn = await _adapter().complete_turn(
        messages=[{"role": "user", "content": "Recover authentication hours."}],
        tools=[_tool()],
    )

    assert turn.provider == "deepseek"
    assert turn.model == "deepseek-test"
    assert turn.input_tokens == 120
    assert turn.output_tokens == 30
    assert turn.tool_calls[0].call_id == "call-1"
    assert turn.tool_calls[0].name == "search_budgets"
    assert turn.tool_calls[0].arguments == {"query": "JWT authentication"}
    assert captured["model"] == "deepseek-test"
    assert captured["tool_choice"] == "auto"
    assert captured["tools"][0]["function"]["strict"] is True


@pytest.mark.asyncio
async def test_litellm_adapter_normalizes_final_text(monkeypatch) -> None:
    async def fake_acompletion(**kwargs):
        return {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": "  Recovery complete.  ",
                        "tool_calls": [],
                    },
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 4},
        }

    monkeypatch.setattr(adapter_module.litellm, "acompletion", fake_acompletion)

    turn = await _adapter().complete_turn(
        messages=[{"role": "user", "content": "Finish."}],
        tools=[],
    )

    assert turn.content == "Recovery complete."
    assert turn.tool_calls == []
    assert turn.finish_reason == "stop"


@pytest.mark.asyncio
async def test_litellm_adapter_rejects_non_json_tool_arguments(monkeypatch) -> None:
    async def fake_acompletion(**kwargs):
        return {
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "function": {
                                    "name": "search_budgets",
                                    "arguments": "not-json",
                                },
                            }
                        ],
                    },
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }

    monkeypatch.setattr(adapter_module.litellm, "acompletion", fake_acompletion)

    with pytest.raises(AgentProviderContractError, match="not valid JSON"):
        await _adapter().complete_turn(
            messages=[{"role": "user", "content": "Break arguments."}],
            tools=[_tool()],
        )


@pytest.mark.asyncio
async def test_litellm_adapter_rejects_missing_choice(monkeypatch) -> None:
    async def fake_acompletion(**kwargs):
        return {"choices": [], "usage": {}}

    monkeypatch.setattr(adapter_module.litellm, "acompletion", fake_acompletion)

    with pytest.raises(AgentProviderContractError, match="first choice"):
        await _adapter().complete_turn(
            messages=[{"role": "user", "content": "No choice."}],
            tools=[],
        )
