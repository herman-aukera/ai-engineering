from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.energy_chat.baseline import (
    build_deepseek_baseline_messages,
    generate_deepseek_baseline_draft,
)
from app.energy_chat.contracts import DeepSeekBaselineRequest


class FakeDraftProvider:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def complete_messages(self, *, messages, tier, max_tokens):
        self.calls.append(
            {
                "messages": messages,
                "tier": tier,
                "max_tokens": max_tokens,
            }
        )
        return {
            "estimation": "This is a plain DeepSeek baseline draft.",
            "provider": "deepseek",
            "model": "deepseek-v4-flash",
            "tier": tier,
            "input_tokens": 42,
            "output_tokens": 13,
            "cost_usd": 0.0001,
            "finish_reason": "stop",
        }


def test_build_deepseek_baseline_messages_preserves_constraints():
    request = DeepSeekBaselineRequest(
        user_message="Explain whether this release is ready.",
        required_constraints=["Mention missing validation evidence."],
        required_sections=["Decision", "Next action"],
    )

    messages = build_deepseek_baseline_messages(request)

    assert messages[0]["role"] == "system"
    assert "plain DeepSeek baseline" in messages[0]["content"]
    assert "Do not evaluate yourself" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "Mention missing validation evidence" in messages[1]["content"]
    assert "Decision" in messages[1]["content"]
    assert "Next action" in messages[1]["content"]


def test_generate_deepseek_baseline_draft_uses_injected_provider():
    provider = FakeDraftProvider()
    request = DeepSeekBaselineRequest(user_message="Draft a release readiness answer.")

    result = generate_deepseek_baseline_draft(request, provider=provider)

    assert result.draft_answer == "This is a plain DeepSeek baseline draft."
    assert result.provider == "deepseek"
    assert result.model == "deepseek-v4-flash"
    assert result.tier == "flash"
    assert result.input_tokens == 42
    assert result.output_tokens == 13
    assert result.cost_usd == 0.0001
    assert result.evidence_refs == ["provider:deepseek_baseline", "tier:flash"]
    assert result.metadata["energy_evaluated"] is False
    assert provider.calls[0]["tier"] == "flash"
    assert provider.calls[0]["max_tokens"] == request.max_tokens


def test_deepseek_baseline_request_rejects_non_deepseek_tiers():
    with pytest.raises(ValidationError):
        DeepSeekBaselineRequest(
            user_message="This should not route to a backup provider.",
            tier="backup",
        )


def test_generate_deepseek_baseline_draft_rejects_empty_provider_output():
    class EmptyProvider:
        def complete_messages(self, *, messages, tier, max_tokens):
            return {"estimation": "   ", "provider": "deepseek", "model": "deepseek-v4-flash"}

    request = DeepSeekBaselineRequest(user_message="Draft something.")

    with pytest.raises(RuntimeError, match="no visible draft answer"):
        generate_deepseek_baseline_draft(request, provider=EmptyProvider())
