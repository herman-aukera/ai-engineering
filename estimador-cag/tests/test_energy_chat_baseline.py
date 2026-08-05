from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.energy_chat.baseline import (
    BASELINE_TIER_LADDER,
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


class FallbackDraftProvider:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def complete_with_fallback_messages(self, *, messages, starting_tier, tier_ladder, max_tokens):
        self.calls.append(
            {
                "messages": messages,
                "starting_tier": starting_tier,
                "tier_ladder": tier_ladder,
                "max_tokens": max_tokens,
            }
        )
        return {
            "estimation": "This draft came from the Kimi fallback tier.",
            "provider": "kimi",
            "model": "moonshot/kimi-k2.5",
            "tier": "backup",
            "input_tokens": 50,
            "output_tokens": 11,
            "cost_usd": 0.0002,
            "finish_reason": "stop",
            "fallback_used": True,
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
    assert result.fallback_used is False
    assert result.evidence_refs == ["provider:deepseek_baseline", "tier:flash"]
    assert result.metadata["energy_evaluated"] is False
    assert result.metadata["fallback_capable"] is False
    assert provider.calls[0]["tier"] == "flash"
    assert provider.calls[0]["max_tokens"] == request.max_tokens


def test_generate_deepseek_baseline_draft_uses_kimi_fallback_when_primary_fails():
    provider = FallbackDraftProvider()
    request = DeepSeekBaselineRequest(user_message="Draft a release readiness answer.")

    result = generate_deepseek_baseline_draft(request, provider=provider)

    assert result.draft_answer == "This draft came from the Kimi fallback tier."
    assert result.provider == "kimi"
    assert result.model == "moonshot/kimi-k2.5"
    assert result.tier == "backup"
    assert result.fallback_used is True
    assert result.evidence_refs == [
        "provider:deepseek_baseline",
        "tier:backup",
        "fallback_from:flash",
    ]
    assert result.metadata["fallback_capable"] is True
    assert result.metadata["requested_tier"] == "flash"
    assert result.metadata["resolved_tier"] == "backup"
    assert result.metadata["tier_ladder"] == list(BASELINE_TIER_LADDER)
    assert provider.calls[0]["starting_tier"] == "flash"
    assert provider.calls[0]["tier_ladder"] == list(BASELINE_TIER_LADDER)


def test_deepseek_baseline_request_rejects_non_deepseek_tiers():
    with pytest.raises(ValidationError):
        DeepSeekBaselineRequest(
            user_message="This should not route directly to a backup provider.",
            tier="backup",
        )


def test_generate_deepseek_baseline_draft_rejects_empty_provider_output():
    class EmptyProvider:
        def complete_messages(self, *, messages, tier, max_tokens):
            return {"estimation": "   ", "provider": "deepseek", "model": "deepseek-v4-flash"}

    request = DeepSeekBaselineRequest(user_message="Draft something.")

    with pytest.raises(RuntimeError, match="no visible draft answer"):
        generate_deepseek_baseline_draft(request, provider=EmptyProvider())
