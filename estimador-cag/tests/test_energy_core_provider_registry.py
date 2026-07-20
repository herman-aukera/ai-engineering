"""Tests for the provider capability registry and selector.

All tests are deterministic — no live API calls, no provider keys required.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from energy_core.provider_registry import (
    CapabilityRegistry,
    ModelCapability,
    PricingSnapshot,
    ProviderSelection,
    ProviderSelector,
    ResolvedProvider,
    _build_default_registry,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _registry() -> CapabilityRegistry:
    return CapabilityRegistry()


def _selector() -> ProviderSelector:
    return ProviderSelector()


def _selection(**overrides) -> ProviderSelection:
    payload: dict = {"provider": "auto", "profile": "medium"}
    payload.update(overrides)
    return ProviderSelection.model_validate(payload)


# ------------------------------------------------------------------
# Registry: default capabilities
# ------------------------------------------------------------------


def test_registry_loads_default_capabilities() -> None:
    """Default registry must contain all curated entries."""
    registry = _registry()
    models = registry.list_available_models()
    model_ids = {m.model_id for m in models}

    assert "deepseek-v4-flash" in model_ids
    assert "deepseek-v4-pro" in model_ids
    assert "kimi-k3" in model_ids
    assert "kimi-for-coding" in model_ids
    assert "gpt-5.6-luna" in model_ids
    assert "gpt-5.6-terra" in model_ids
    assert "gpt-5.6-sol" in model_ids
    assert len(models) >= 7


def test_registry_get_known_model() -> None:
    """get() must return ModelCapability for known model_ids."""
    registry = _registry()
    cap = registry.get("deepseek-v4-pro")
    assert cap is not None
    assert cap.provider == "deepseek"
    assert cap.model_family == "deepseek-v4"
    assert cap.context_window == 128_000


def test_registry_get_unknown_model_returns_none() -> None:
    """get() must return None for unknown model_ids."""
    registry = _registry()
    assert registry.get("nonexistent-model") is None


def test_registry_list_provider_models() -> None:
    """list_provider_models must return all models for a provider."""
    registry = _registry()
    deepseek_models = registry.list_provider_models("deepseek")
    model_ids = {m.model_id for m in deepseek_models}
    assert "deepseek-v4-flash" in model_ids
    assert "deepseek-v4-pro" in model_ids


def test_registry_list_available_models_excludes_unavailable() -> None:
    """list_available_models must exclude unavailable models."""
    caps = _build_default_registry()
    caps["deepseek-v4-pro"] = caps["deepseek-v4-pro"].model_copy(
        update={"availability_state": "unavailable"}
    )
    registry = CapabilityRegistry(caps)
    available = registry.list_available_models()
    available_ids = {m.model_id for m in available}
    assert "deepseek-v4-pro" not in available_ids
    assert "deepseek-v4-flash" in available_ids


# ------------------------------------------------------------------
# Profile resolution: DeepSeek
# ------------------------------------------------------------------


def test_resolve_deepseek_minimal() -> None:
    """DeepSeek minimal must resolve to v4-flash, non-thinking, high effort."""
    registry = _registry()
    model_id, mode, effort = registry.resolve_profile("deepseek", "minimal")
    assert model_id == "deepseek-v4-flash"
    assert mode == "non-thinking"
    assert effort == "high"


def test_resolve_deepseek_medium() -> None:
    """DeepSeek medium must resolve to v4-flash, thinking, high effort."""
    registry = _registry()
    model_id, mode, effort = registry.resolve_profile("deepseek", "medium")
    assert model_id == "deepseek-v4-flash"
    assert mode == "thinking"
    assert effort == "high"


def test_resolve_deepseek_max() -> None:
    """DeepSeek max must resolve to v4-pro, thinking, max effort."""
    registry = _registry()
    model_id, mode, effort = registry.resolve_profile("deepseek", "max")
    assert model_id == "deepseek-v4-pro"
    assert mode == "thinking"
    assert effort == "max"


# ------------------------------------------------------------------
# Profile resolution: Kimi
# ------------------------------------------------------------------


def test_resolve_kimi_minimal() -> None:
    """Kimi minimal must resolve to kimi-for-coding."""
    registry = _registry()
    model_id, mode, effort = registry.resolve_profile("kimi", "minimal")
    assert model_id == "kimi-for-coding"
    assert effort == "medium"


def test_resolve_kimi_max() -> None:
    """Kimi max must resolve to kimi-k3, max effort."""
    registry = _registry()
    model_id, mode, effort = registry.resolve_profile("kimi", "max")
    assert model_id == "kimi-k3"
    assert effort == "max"


# ------------------------------------------------------------------
# Profile resolution: OpenAI
# ------------------------------------------------------------------


def test_resolve_openai_minimal() -> None:
    """OpenAI minimal must resolve to gpt-5.6-luna, non-thinking, low effort."""
    registry = _registry()
    model_id, mode, effort = registry.resolve_profile("openai", "minimal")
    assert model_id == "gpt-5.6-luna"
    assert mode == "non-thinking"
    assert effort == "low"


def test_resolve_openai_max() -> None:
    """OpenAI max must resolve to gpt-5.6-sol, thinking, max effort."""
    registry = _registry()
    model_id, mode, effort = registry.resolve_profile("openai", "max")
    assert model_id == "gpt-5.6-sol"
    assert mode == "thinking"
    assert effort == "max"


# ------------------------------------------------------------------
# Unsupported combinations fail closed
# ------------------------------------------------------------------


def test_invalid_provider_fails_closed() -> None:
    """Unknown provider must raise ValueError."""
    with pytest.raises(ValueError, match="Unsupported provider"):
        _registry().resolve_profile("unknown", "medium")


def test_unavailable_model_fails_closed() -> None:
    """Unavailable model must raise ValueError."""
    caps = _build_default_registry()
    caps["deepseek-v4-flash"] = caps["deepseek-v4-flash"].model_copy(
        update={"availability_state": "unavailable"}
    )
    registry = CapabilityRegistry(caps)
    with pytest.raises(ValueError, match="unavailable"):
        registry.resolve_profile("deepseek", "minimal")


# ------------------------------------------------------------------
# Provider selector: auto routing
# ------------------------------------------------------------------


def test_auto_provider_selects_deepseek() -> None:
    """Auto provider must default to DeepSeek for normal requests."""
    selector = _selector()
    result = selector.select(_selection(provider="auto", profile="medium"))
    assert result.provider == "deepseek"
    assert result.model_id == "deepseek-v4-flash"
    assert result.fallback_used is False


def test_explicit_deepseek_selects_correctly() -> None:
    """Explicit deepseek provider must resolve correctly."""
    selector = _selector()
    result = selector.select(_selection(provider="deepseek", profile="max"))
    assert result.provider == "deepseek"
    assert result.model_id == "deepseek-v4-pro"


def test_explicit_kimi_selects_correctly() -> None:
    """Explicit kimi provider must resolve correctly."""
    selector = _selector()
    result = selector.select(_selection(provider="kimi", profile="max"))
    assert result.provider == "kimi"
    assert result.model_id == "kimi-k3"


def test_explicit_openai_selects_correctly() -> None:
    """Explicit openai provider must resolve correctly."""
    selector = _selector()
    result = selector.select(_selection(provider="openai", profile="medium"))
    assert result.provider == "openai"
    assert result.model_id == "gpt-5.6-terra"


# ------------------------------------------------------------------
# Budget enforcement
# ------------------------------------------------------------------


def test_openai_escalation_exceeding_budget_fails() -> None:
    """OpenAI with insufficient budget must fail closed."""
    selector = _selector()
    with pytest.raises(ValueError, match="budget"):
        selector.select(_selection(
            provider="openai",
            profile="max",
            max_cost_usd=Decimal("0.00001"),  # Extremely low budget
        ))


# ------------------------------------------------------------------
# Fallback behavior
# ------------------------------------------------------------------


def test_cross_provider_fallback_succeeds() -> None:
    """governed_cross_provider fallback must resolve to next provider."""
    caps = _build_default_registry()
    # Make deepseek unavailable
    for kid in list(caps):
        if caps[kid].provider == "deepseek":
            caps[kid] = caps[kid].model_copy(update={"availability_state": "unavailable"})
    registry = CapabilityRegistry(caps)
    selector = ProviderSelector(registry)

    result = selector.select(_selection(
        provider="deepseek",
        profile="medium",
        fallback_policy="governed_cross_provider",
    ))
    assert result.fallback_used is True
    assert result.provider == "kimi"
    assert result.fallback_reason is not None


def test_no_fallback_policy_fails_when_unresolvable() -> None:
    """fallback_policy=none must raise when provider cannot resolve."""
    caps = _build_default_registry()
    for kid in list(caps):
        if caps[kid].provider == "deepseek":
            caps[kid] = caps[kid].model_copy(update={"availability_state": "unavailable"})
    registry = CapabilityRegistry(caps)
    selector = ProviderSelector(registry)

    with pytest.raises(ValueError):
        selector.select(_selection(
            provider="deepseek",
            profile="medium",
            fallback_policy="none",
        ))


# ------------------------------------------------------------------
# Serialization
# ------------------------------------------------------------------


def test_model_capability_round_trips() -> None:
    """ModelCapability must serialize and deserialize correctly."""
    cap = ModelCapability(
        provider="test",
        model_id="test-model-1",
        model_family="test-family",
        context_window=64_000,
        max_output_tokens=4_096,
        reasoning_efforts=("low", "high"),
    )
    dumped = cap.model_dump(mode="json")
    reloaded = ModelCapability.model_validate(dumped)
    assert reloaded.model_id == "test-model-1"
    assert reloaded.context_window == 64_000


def test_resolved_provider_round_trips() -> None:
    """ResolvedProvider must serialize and deserialize correctly."""
    rp = ResolvedProvider(
        provider="deepseek",
        model_id="deepseek-v4-pro",
        reasoning_mode="thinking",
        reasoning_effort="max",
        profile="max",
        estimated_cost_ceiling_usd=Decimal("1.00"),
        capability_snapshot_hash="abc123",
    )
    dumped = rp.model_dump(mode="json")
    reloaded = ResolvedProvider.model_validate(dumped)
    assert reloaded.provider == "deepseek"
    assert reloaded.capability_snapshot_hash == "abc123"


def test_provider_selection_round_trips() -> None:
    """ProviderSelection must serialize and deserialize correctly."""
    sel = ProviderSelection(
        provider="kimi",
        profile="max",
        fallback_policy="governed_cross_provider",
    )
    dumped = sel.model_dump(mode="json")
    reloaded = ProviderSelection.model_validate(dumped)
    assert reloaded.provider == "kimi"
    assert reloaded.fallback_policy == "governed_cross_provider"


# ------------------------------------------------------------------
# Pricing defaults
# ------------------------------------------------------------------


def test_pricing_snapshot_defaults() -> None:
    """PricingSnapshot defaults must be zero."""
    ps = PricingSnapshot()
    assert ps.input_price_per_1k_tokens == Decimal("0.0")
    assert ps.output_price_per_1k_tokens == Decimal("0.0")


# ------------------------------------------------------------------
# Capability hash is deterministic
# ------------------------------------------------------------------


def test_capability_snapshot_hash_is_deterministic() -> None:
    """Same selection must produce same capability snapshot hash."""
    selector = _selector()
    r1 = selector.select(_selection(provider="kimi", profile="max"))
    r2 = selector.select(_selection(provider="kimi", profile="max"))
    assert r1.capability_snapshot_hash == r2.capability_snapshot_hash


def test_different_selections_produce_different_hashes() -> None:
    """Different selections must produce different capability snapshot hashes."""
    selector = _selector()
    r1 = selector.select(_selection(provider="kimi", profile="max"))
    r2 = selector.select(_selection(provider="openai", profile="max"))
    assert r1.capability_snapshot_hash != r2.capability_snapshot_hash


# ------------------------------------------------------------------
# Effort coercion is validated
# ------------------------------------------------------------------


def test_kimi_k3_only_supports_max_effort() -> None:
    """Kimi K3 must only support max effort per verified documentation."""
    cap = _registry().get("kimi-k3")
    assert cap is not None
    assert cap.reasoning_efforts == ("max",)
    # kimi/medium resolves to kimi-for-coding (not k3), with high effort
    model_id, mode, effort = _registry().resolve_profile("kimi", "medium")
    assert model_id == "kimi-for-coding"
    assert effort == "high"
    # kimi/max resolves to kimi-k3 with max effort
    model_id, mode, effort = _registry().resolve_profile("kimi", "max")
    assert model_id == "kimi-k3"
    assert effort == "max"


# ------------------------------------------------------------------
# DeepSeek effort coercion is documented
# ------------------------------------------------------------------


def test_deepseek_effort_coercion() -> None:
    """DeepSeek profiles must coerce efforts correctly:
    minimal/medium -> high, max -> max"""
    reg = _registry()
    cap = reg.get("deepseek-v4-flash")
    assert cap is not None
    # Flash only supports high and max
    assert "low" not in cap.reasoning_efforts
    assert "medium" not in cap.reasoning_efforts
    assert "high" in cap.reasoning_efforts
    assert "max" in cap.reasoning_efforts


# ------------------------------------------------------------------
# Default registry builder
# ------------------------------------------------------------------


def test_default_registry_builder_returns_dict() -> None:
    """_build_default_registry must return a non-empty dict."""
    caps = _build_default_registry()
    assert isinstance(caps, dict)
    assert len(caps) >= 7


# ------------------------------------------------------------------
# Context profile is preserved
# ------------------------------------------------------------------


def test_context_profile_is_preserved_in_selection() -> None:
    """context_profile must survive serialization."""
    sel = ProviderSelection(context_profile="max")
    assert sel.context_profile == "max"
