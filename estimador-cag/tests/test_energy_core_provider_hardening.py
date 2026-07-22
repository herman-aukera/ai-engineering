"""Deterministic provider-hardening tests. No network calls are made."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import pytest

from energy_core.live_adapter import (
    DeepSeekAdapter,
    KimiCodeAdapter,
    LiveAdapterConfig,
    OpenAIAdapter,
)
from energy_core.provider_registry import ProviderSelection
from energy_core.provider_verified import VerifiedCapabilityRegistry


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def _capture_urlopen(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, Any],
) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    def fake_urlopen(request: Any, *, timeout: float) -> FakeResponse:
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse(payload)

    monkeypatch.setattr(
        "energy_core.live_adapter_v2.urllib.request.urlopen",
        fake_urlopen,
    )
    return captured


def test_verified_registry_uses_current_price_units_and_values() -> None:
    registry = VerifiedCapabilityRegistry()

    deepseek = registry.get("deepseek-v4-pro")
    luna = registry.get("gpt-5.6-luna")
    terra = registry.get("gpt-5.6-terra")
    sol = registry.get("gpt-5.6-sol")

    assert deepseek is not None
    assert deepseek.pricing.price_unit == "per_1K_tokens"
    assert deepseek.pricing.input_price_per_1k_tokens == Decimal("0.000435")
    assert deepseek.pricing.cached_input_price_per_1k_tokens == Decimal("0.000003625")
    assert deepseek.pricing.output_price_per_1k_tokens == Decimal("0.00087")

    assert luna is not None and luna.pricing.input_price_per_1k_tokens == Decimal("0.001")
    assert terra is not None and terra.pricing.output_price_per_1k_tokens == Decimal("0.015")
    assert sol is not None and sol.pricing.output_price_per_1k_tokens == Decimal("0.03")


def test_verified_kimi_code_contract_is_conservative_and_surface_specific() -> None:
    registry = VerifiedCapabilityRegistry()
    k3 = registry.get("k3")
    k2 = registry.get("kimi-for-coding")
    platform = registry.get("kimi-k3")

    assert k3 is not None
    assert k3.surface == "kimi_code"
    assert k3.context_window == 262_144
    assert k3.reasoning_efforts == ("low", "high", "max")
    assert k2 is not None and k2.reasoning_efforts == ()
    assert platform is not None and platform.freshness_state == "unverified"


def test_deepseek_request_sends_thinking_effort_and_converts_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    captured = _capture_urlopen(
        monkeypatch,
        {
            "id": "deepseek-request",
            "model": "deepseek-v4-flash",
            "reasoning_effort": "high",
            "usage": {
                "prompt_tokens": 1000,
                "prompt_cache_hit_tokens": 100,
                "completion_tokens": 200,
            },
        },
    )
    adapter = DeepSeekAdapter(
        LiveAdapterConfig(
            enabled=True,
            provider="deepseek",
            api_key_env_var="DEEPSEEK_API_KEY",
        )
    )

    evidence = adapter.invoke(
        ProviderSelection(
            provider="deepseek",
            profile="medium",
            max_latency_ms=2500,
        )
    )

    assert captured["url"] == "https://api.deepseek.com/v1/chat/completions"
    assert captured["timeout"] == 2.5
    assert captured["body"]["thinking"] == {"type": "enabled"}
    assert captured["body"]["reasoning_effort"] == "high"
    assert "temperature" not in captured["body"]
    assert evidence.served_effort == "high"
    assert evidence.execution_performed is True


def test_kimi_code_uses_membership_endpoint_and_k3_effort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KIMI_API_KEY", "test-key")
    captured = _capture_urlopen(
        monkeypatch,
        {
            "id": "kimi-request",
            "model": "k3",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        },
    )
    adapter = KimiCodeAdapter(
        LiveAdapterConfig(
            enabled=True,
            provider="kimi",
            api_key_env_var="KIMI_API_KEY",
        )
    )

    evidence = adapter.invoke(
        ProviderSelection(provider="kimi", profile="max", max_latency_ms=10_000)
    )

    assert captured["url"] == "https://api.kimi.com/coding/v1/chat/completions"
    assert captured["body"]["model"] == "k3"
    assert captured["body"]["reasoning_effort"] == "max"
    assert evidence.served_model_id == "k3"
    assert evidence.served_effort == ""


def test_openai_effort_is_planned_but_not_claimed_as_served_without_echo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured = _capture_urlopen(
        monkeypatch,
        {
            "id": "openai-request",
            "model": "gpt-5.6-terra",
            "usage": {
                "prompt_tokens": 1000,
                "prompt_tokens_details": {"cached_tokens": 250},
                "completion_tokens": 100,
            },
        },
    )
    adapter = OpenAIAdapter(
        LiveAdapterConfig(
            enabled=True,
            provider="openai",
            api_key_env_var="OPENAI_API_KEY",
        )
    )

    evidence = adapter.invoke(
        ProviderSelection(provider="openai", profile="medium", max_cost_usd=Decimal("5"))
    )

    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["body"]["reasoning_effort"] == "medium"
    assert evidence.planned_effort == "medium"
    assert evidence.served_effort == ""
    assert evidence.tokens.cached_input_tokens == 250
    assert evidence.cost_usd > Decimal("0")
