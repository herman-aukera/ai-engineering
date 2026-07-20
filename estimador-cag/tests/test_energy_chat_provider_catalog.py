"""Milestone 17: provider catalog — capability records, effort resolution, verification."""

from __future__ import annotations

from app.energy_chat.provider_catalog import (
    get_catalog,
    resolve_effort_profile,
)


def test_catalog_includes_verified_deepseek_models() -> None:
    catalog = get_catalog()
    assert "deepseek" in catalog
    assert "deepseek-v4-flash" in catalog["deepseek"]
    assert "deepseek-v4-pro" in catalog["deepseek"]
    assert catalog["deepseek"]["deepseek-v4-flash"].availability_status == "verified"
    assert catalog["deepseek"]["deepseek-v4-pro"].availability_status == "verified"


def test_catalog_includes_documented_kimi_and_openai() -> None:
    catalog = get_catalog()
    assert "kimi" in catalog
    assert "openai" in catalog
    kimi = catalog["kimi"]["kimi-k3-preview"]
    assert kimi.availability_status == "documented"
    # Documented models must not be treated as verified
    assert kimi.availability_status != "verified"


def test_catalog_entries_have_source_refs() -> None:
    catalog = get_catalog()
    for provider_models in catalog.values():
        for model in provider_models.values():
            assert model.source_refs, f"{model.model_id} missing source_refs"
            assert model.verified_at, f"{model.model_id} missing verified_at"


def test_catalog_entries_have_supported_effort_profiles() -> None:
    catalog = get_catalog()
    flash = catalog["deepseek"]["deepseek-v4-flash"]
    pro = catalog["deepseek"]["deepseek-v4-pro"]
    assert "fast" in flash.supported_effort_profiles
    assert "balanced" in flash.supported_effort_profiles
    assert "balanced" in pro.supported_effort_profiles
    assert "max" in pro.supported_effort_profiles


def test_resolve_effort_finds_cheapest_verified_model() -> None:
    result = resolve_effort_profile("deepseek", "fast")
    assert result is not None
    assert result.model_id == "deepseek-v4-flash"


def test_resolve_effort_finds_pro_for_max() -> None:
    result = resolve_effort_profile("deepseek", "max")
    assert result is not None
    assert result.model_id == "deepseek-v4-pro"


def test_resolve_effort_returns_none_for_documented_only() -> None:
    """Documented (not verified) models must not be returned by resolve."""
    result = resolve_effort_profile("kimi", "balanced")
    assert result is None


def test_resolve_effort_returns_none_for_unknown_provider() -> None:
    result = resolve_effort_profile("unknown", "balanced")
    assert result is None
