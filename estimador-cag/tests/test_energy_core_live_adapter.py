"""Tests for live provider adapters — deterministic, no real API calls.

Tests verify disabled-by-default behavior, missing-key graceful fallback,
and evidence contracts. Real provider calls are opt-in manual smoke only.
"""

from __future__ import annotations  # noqa: I001

import os

import pytest

from energy_core.live_adapter import DeepSeekAdapter, LiveAdapterConfig
from energy_core.provider_registry import ProviderSelection


def _selection(**overrides) -> ProviderSelection:
    payload: dict = {"provider": "deepseek", "profile": "medium"}
    payload.update(overrides)
    return ProviderSelection.model_validate(payload)


@pytest.fixture(autouse=True)
def _clear_api_key() -> None:
    """Ensure DEEPSEEK_API_KEY is cleared before each test."""
    old = os.environ.pop("DEEPSEEK_API_KEY", None)
    yield
    if old is not None:
        os.environ["DEEPSEEK_API_KEY"] = old


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
