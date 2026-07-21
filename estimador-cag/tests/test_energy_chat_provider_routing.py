"""Tests for strict provider catalog v2 effort routing."""

from __future__ import annotations

from app.energy_chat.provider_catalog import (
    DEEPSEEK_V4_FLASH,
    DEEPSEEK_V4_PRO,
    GPT56_LUNA,
    GPT56_SOL,
    GPT56_TERRA,
    KIMI_K3,
    get_catalog,
    resolve_effort_profile,
)


def test_deepseek_effort_mapping() -> None:
    fast = resolve_effort_profile("deepseek", "fast")
    balanced = resolve_effort_profile("deepseek", "balanced")
    maximum = resolve_effort_profile("deepseek", "max")

    assert fast is not None
    assert balanced is not None
    assert maximum is not None
    assert fast.capability == DEEPSEEK_V4_FLASH
    assert fast.provider_parameters == {"thinking": "disabled"}
    assert balanced.capability == DEEPSEEK_V4_FLASH
    assert balanced.provider_parameters == {"thinking": "enabled"}
    assert maximum.capability == DEEPSEEK_V4_PRO
    assert maximum.provider_parameters == {"thinking": "enabled"}


def test_kimi_effort_mapping_uses_verified_platform_surface() -> None:
    expected = {"fast": "low", "balanced": "high", "max": "max"}
    for effort, reasoning in expected.items():
        profile = resolve_effort_profile("kimi", effort)
        assert profile is not None
        assert profile.capability == KIMI_K3
        assert profile.capability.model_id == "kimi-k3"
        assert profile.capability.api_surface == "kimi_platform_openai_compatible"
        assert profile.provider_parameters == {"reasoning_effort": reasoning}


def test_openai_effort_mapping() -> None:
    fast = resolve_effort_profile("openai", "fast")
    balanced = resolve_effort_profile("openai", "balanced")
    maximum = resolve_effort_profile("openai", "max")

    assert fast is not None
    assert balanced is not None
    assert maximum is not None
    assert fast.capability == GPT56_LUNA
    assert balanced.capability == GPT56_TERRA
    assert maximum.capability == GPT56_SOL
    assert maximum.provider_parameters == {"reasoning": {"effort": "max"}}


def test_unknown_provider_returns_none() -> None:
    assert resolve_effort_profile("unknown", "balanced") is None  # type: ignore[arg-type]


def test_catalog_is_versioned_and_provider_namespaced() -> None:
    catalog = get_catalog()
    assert "deepseek" in catalog
    assert "kimi" in catalog
    assert "openai" in catalog
    assert catalog["deepseek"]["deepseek-v4-flash"].catalog_version == "2.0.0"
    assert catalog["kimi"]["kimi-k3"].eligible_for_eachat is True
    assert catalog["kimi"]["k3"].eligible_for_eachat is False


def test_strict_v2_resolver_does_not_accept_custom_v1_catalogs() -> None:
    profile = resolve_effort_profile(
        "deepseek",
        "fast",
        catalog={"ignored": {}},  # type: ignore[arg-type]
    )
    assert profile is not None
    assert profile.capability == DEEPSEEK_V4_FLASH
    assert profile.capability.catalog_version == "2.0.0"
