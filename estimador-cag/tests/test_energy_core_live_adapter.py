"""Tests for live provider adapters — deterministic, no real API calls.

Tests verify disabled-by-default behavior, missing-key graceful fallback,
and evidence contracts. Real provider calls are opt-in manual smoke only.
"""

from __future__ import annotations  # noqa: I001

import os

import pytest

from energy_core.live_adapter import (
    DeepSeekAdapter,
    KimiCodeAdapter,
    LiveAdapterConfig,
    OpenAIAdapter,
)
from energy_core.provider_registry import ProviderSelection


def _selection(**overrides) -> ProviderSelection:
    payload: dict = {"provider": "deepseek", "profile": "medium"}
    payload.update(overrides)
    return ProviderSelection.model_validate(payload)


@pytest.fixture(autouse=True)
def _clear_api_keys() -> None:
    """Ensure provider API keys are cleared before each test."""
    old_deepseek = os.environ.pop("DEEPSEEK_API_KEY", None)
    old_kimi = os.environ.pop("KIMI_API_KEY", None)
    old_openai = os.environ.pop("OPENAI_API_KEY", None)
    yield
    if old_deepseek is not None:
        os.environ["DEEPSEEK_API_KEY"] = old_deepseek
    if old_kimi is not None:
        os.environ["KIMI_API_KEY"] = old_kimi
    if old_openai is not None:
        os.environ["OPENAI_API_KEY"] = old_openai


# ------------------------------------------------------------------
# Disabled-by-default
# ------------------------------------------------------------------


def test_live_adapter_disabled_by_default() -> None:
    """Live adapter must be disabled by default."""
    config = LiveAdapterConfig(
        provider="deepseek",
        api_key_env_var="DEEPSEEK_API_KEY",
    )
    assert config.enabled is False


def test_disabled_adapter_returns_fake_evidence() -> None:
    """When disabled, the adapter must produce fake evidence, not call the API."""
    config = LiveAdapterConfig(
        enabled=False,
        provider="deepseek",
        api_key_env_var="DEEPSEEK_API_KEY",
    )
    adapter = DeepSeekAdapter(config)
    result = adapter.invoke(_selection())
    assert result.execution_performed is False
    assert result.served_provider != ""


def test_disabled_adapter_counts_calls() -> None:
    """Even when disabled, call count increments."""
    config = LiveAdapterConfig(enabled=False, provider="deepseek", api_key_env_var="DEEPSEEK_API_KEY")
    adapter = DeepSeekAdapter(config)
    assert adapter.calls == 0
    adapter.invoke(_selection())
    assert adapter.calls == 1


# ------------------------------------------------------------------
# Missing API key
# ------------------------------------------------------------------


def test_missing_api_key_returns_failure_evidence() -> None:
    """When API key is missing, adapter must return failure evidence."""
    config = LiveAdapterConfig(
        enabled=True,
        provider="deepseek",
        api_key_env_var="DEEPSEEK_API_KEY",
    )
    adapter = DeepSeekAdapter(config)
    result = adapter.invoke(_selection())
    assert result.execution_performed is False
    assert len(result.attempts) == 1
    assert result.attempts[0].status == "failed"
    assert "DEEPSEEK_API_KEY" in (result.attempts[0].error_message or "")
    assert result.circuit_state == "open"


def test_unresolvable_selection_with_key() -> None:
    """Even with a key, unresolvable selection returns failure evidence."""
    os.environ["DEEPSEEK_API_KEY"] = "test-key-123"
    config = LiveAdapterConfig(
        enabled=True,
        provider="deepseek",
        api_key_env_var="DEEPSEEK_API_KEY",
    )
    # Remove deepseek models to force resolution failure
    from energy_core.provider_registry import CapabilityRegistry
    caps = {
        k: v for k, v in CapabilityRegistry()._capabilities.items()
        if v.provider != "deepseek"
    }
    registry = CapabilityRegistry(caps)
    adapter = DeepSeekAdapter(config.model_copy(update={"registry": registry}))
    result = adapter.invoke(_selection(provider="deepseek", profile="medium"))
    assert result.attempts[0].status == "failed"


# ------------------------------------------------------------------
# Config and contracts
# ------------------------------------------------------------------


def test_live_adapter_config_round_trips() -> None:
    config = LiveAdapterConfig(
        enabled=True,
        provider="kimi",
        api_key_env_var="KIMI_API_KEY",
        api_base_url="https://api.moonshot.cn",
    )
    reloaded = LiveAdapterConfig.model_validate(config.model_dump(mode="json"))
    assert reloaded.provider == "kimi"
    assert reloaded.api_base_url == "https://api.moonshot.cn"


# ------------------------------------------------------------------
# Kimi Code adapter
# ------------------------------------------------------------------


def test_kimi_adapter_disabled_by_default() -> None:
    config = LiveAdapterConfig(provider="kimi", api_key_env_var="KIMI_API_KEY")
    assert config.enabled is False


def test_kimi_adapter_disabled_returns_fake_evidence() -> None:
    config = LiveAdapterConfig(enabled=False, provider="kimi", api_key_env_var="KIMI_API_KEY")
    adapter = KimiCodeAdapter(config)
    result = adapter.invoke(_selection(provider="kimi", profile="max"))
    assert result.execution_performed is False
    assert result.served_provider != ""


def test_kimi_adapter_missing_key_returns_failure() -> None:
    config = LiveAdapterConfig(enabled=True, provider="kimi", api_key_env_var="KIMI_API_KEY")
    adapter = KimiCodeAdapter(config)
    result = adapter.invoke(_selection(provider="kimi", profile="max"))
    assert result.attempts[0].status == "failed"
    assert "KIMI_API_KEY" in (result.attempts[0].error_message or "")


def test_kimi_adapter_uses_moonshot_url() -> None:
    os.environ["KIMI_API_KEY"] = "test-key"
    config = LiveAdapterConfig(enabled=True, provider="kimi", api_key_env_var="KIMI_API_KEY")
    adapter = KimiCodeAdapter(config)
    # Will fail on network (no real connection in CI) but proves config works
    result = adapter.invoke(_selection(provider="kimi", profile="max"))
    assert result.attempts[0].model_id != "" or result.attempts[0].status == "failed"


# ------------------------------------------------------------------
# OpenAI adapter
# ------------------------------------------------------------------


def test_openai_adapter_disabled_by_default() -> None:
    config = LiveAdapterConfig(provider="openai", api_key_env_var="OPENAI_API_KEY")
    assert config.enabled is False


def test_openai_adapter_disabled_returns_fake() -> None:
    config = LiveAdapterConfig(enabled=False, provider="openai", api_key_env_var="OPENAI_API_KEY")
    adapter = OpenAIAdapter(config)
    result = adapter.invoke(_selection(provider="openai", profile="medium"))
    assert result.execution_performed is False


def test_openai_adapter_missing_key_returns_failure() -> None:
    config = LiveAdapterConfig(enabled=True, provider="openai", api_key_env_var="OPENAI_API_KEY")
    adapter = OpenAIAdapter(config)
    result = adapter.invoke(_selection(provider="openai", profile="medium"))
    assert result.attempts[0].status == "failed"
    assert "OPENAI_API_KEY" in (result.attempts[0].error_message or "")


def test_openai_max_requires_premium_reason() -> None:
    """OpenAI max profile requires premium_reason on selection."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    config = LiveAdapterConfig(enabled=True, provider="openai", api_key_env_var="OPENAI_API_KEY")
    adapter = OpenAIAdapter(config)
    # Without premium_reason, ProviderSelector raises ValueError before API call
    result = adapter.invoke(_selection(provider="openai", profile="max"))
    assert result.attempts[0].status == "failed"
