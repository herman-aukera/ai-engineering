"""Provider catalog facts, surfaces, effort resolution, and claim boundaries."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.energy_chat.provider_catalog import (
    CATALOG_MAX_AGE_DAYS,
    CATALOG_REVIEW_BY,
    CATALOG_VERIFIED_AT,
    CATALOG_VERSION,
    DEEPSEEK_V4_FLASH,
    DEEPSEEK_V4_PRO,
    GPT56_LUNA,
    GPT56_SOL,
    GPT56_TERRA,
    KIMI_CODE_K3,
    KIMI_CODE_K27,
    KIMI_K3_PLATFORM,
    assert_catalog_fresh,
    get_catalog,
    get_provider_models,
    resolve_effort_profile,
)


def test_deepseek_catalog_uses_current_verified_limits_and_prices() -> None:
    assert CATALOG_VERSION == "2.1.0"
    assert DEEPSEEK_V4_FLASH.context_window_tokens == 1_000_000
    assert DEEPSEEK_V4_FLASH.max_output_tokens == 384_000
    assert DEEPSEEK_V4_FLASH.supports_prompt_caching is True
    assert DEEPSEEK_V4_FLASH.input_price_per_million == 0.14
    assert DEEPSEEK_V4_FLASH.cached_input_price_per_million == 0.0028
    assert DEEPSEEK_V4_FLASH.output_price_per_million == 0.28
    assert DEEPSEEK_V4_PRO.context_window_tokens == 1_000_000
    assert DEEPSEEK_V4_PRO.max_output_tokens == 384_000
    assert DEEPSEEK_V4_PRO.input_price_per_million == 0.435
    assert DEEPSEEK_V4_PRO.cached_input_price_per_million == 0.003625
    assert DEEPSEEK_V4_PRO.output_price_per_million == 0.87


def test_kimi_platform_and_kimi_code_are_distinct_surfaces() -> None:
    assert KIMI_K3_PLATFORM.model_id == "kimi-k3"
    assert KIMI_K3_PLATFORM.api_surface == "kimi_platform_openai_compatible"
    assert KIMI_K3_PLATFORM.endpoint_base_url == "https://api.moonshot.ai/v1"
    assert KIMI_K3_PLATFORM.eligible_for_eachat is True
    assert KIMI_K3_PLATFORM.billing_model == "pay_as_you_go"
    assert KIMI_K3_PLATFORM.provider_reasoning_values == ["low", "high", "max"]
    assert KIMI_K3_PLATFORM.context_window_tokens == 1_000_000
    assert KIMI_K3_PLATFORM.max_output_tokens == 1_048_576
    assert KIMI_K3_PLATFORM.input_price_per_million == 3.00
    assert KIMI_K3_PLATFORM.cached_input_price_per_million == 0.30
    assert KIMI_K3_PLATFORM.output_price_per_million == 15.00

    assert KIMI_CODE_K3.model_id == "k3"
    assert KIMI_CODE_K3.api_surface == "kimi_code_anthropic_compatible"
    assert KIMI_CODE_K3.eligible_for_eachat is False
    assert KIMI_CODE_K3.billing_model == "membership_quota"
    assert "Allegretto" in (KIMI_CODE_K3.entitlement_notes or "")
    assert KIMI_CODE_K27.model_id == "kimi-for-coding"
    assert KIMI_CODE_K27.context_window_tokens == 256_000
    assert KIMI_CODE_K27.eligible_for_eachat is False


def test_eachat_provider_listing_excludes_coding_membership_models() -> None:
    eachat_models = get_provider_models("kimi")
    all_kimi_models = get_provider_models("kimi", eachat_only=False)
    assert [item.model_id for item in eachat_models] == ["kimi-k3"]
    assert {item.model_id for item in all_kimi_models} == {
        "kimi-k3",
        "k3",
        "kimi-for-coding",
    }


def test_openai_ga_records_use_current_published_limits_and_prices() -> None:
    assert [GPT56_LUNA.model_id, GPT56_TERRA.model_id, GPT56_SOL.model_id] == [
        "gpt-5.6-luna",
        "gpt-5.6-terra",
        "gpt-5.6-sol",
    ]
    for model in (GPT56_LUNA, GPT56_TERRA, GPT56_SOL):
        assert model.availability_status == "verified"
        assert model.context_window_tokens == 1_050_000
        assert model.max_output_tokens == 128_000
        assert model.modalities == ["text", "image"]
        assert model.provider_reasoning_values == [
            "none",
            "low",
            "medium",
            "high",
            "xhigh",
            "max",
        ]

    assert GPT56_LUNA.input_price_per_million == 0.20
    assert GPT56_LUNA.cached_input_price_per_million == 0.02
    assert GPT56_LUNA.output_price_per_million == 1.20
    assert GPT56_TERRA.input_price_per_million == 2.00
    assert GPT56_TERRA.cached_input_price_per_million == 0.20
    assert GPT56_TERRA.output_price_per_million == 12.00
    assert GPT56_SOL.input_price_per_million == 4.00
    assert GPT56_SOL.cached_input_price_per_million == 0.40
    assert GPT56_SOL.output_price_per_million == 20.00


def test_catalog_entries_are_source_dated_and_surface_specific() -> None:
    catalog = get_catalog()
    for provider_models in catalog.values():
        for model in provider_models.values():
            assert model.source_refs
            assert model.verified_at == CATALOG_VERIFIED_AT == "2026-08-23"
            assert model.catalog_version == CATALOG_VERSION == "2.1.0"
            assert model.api_surface
            assert model.endpoint_base_url.startswith("https://")
            assert model.billing_model
            assert model.adapter_status
            assert model.calibration_status


def test_catalog_freshness_contract_fails_closed_after_review_window() -> None:
    verified = date.fromisoformat(CATALOG_VERIFIED_AT)
    review_by = date.fromisoformat(CATALOG_REVIEW_BY)
    assert review_by - verified == timedelta(days=CATALOG_MAX_AGE_DAYS)

    assert_catalog_fresh(as_of=verified)
    assert_catalog_fresh(as_of=review_by)

    with pytest.raises(RuntimeError, match="stale"):
        assert_catalog_fresh(as_of=review_by + timedelta(days=1))
    with pytest.raises(RuntimeError, match="future"):
        assert_catalog_fresh(as_of=verified - timedelta(days=1))


def test_catalog_temporal_facts_are_current_for_this_ci_run() -> None:
    # Temporal vendor facts are intentionally fail-closed: after REVIEW_BY the
    # deterministic release suite turns RED until an official-source re-audit.
    assert_catalog_fresh(as_of=date.today())


def test_effort_resolution_maps_stable_profiles_deterministically() -> None:
    deepseek_fast = resolve_effort_profile("deepseek", "fast")
    deepseek_balanced = resolve_effort_profile("deepseek", "balanced")
    deepseek_max = resolve_effort_profile("deepseek", "max")
    kimi_fast = resolve_effort_profile("kimi", "fast")
    kimi_balanced = resolve_effort_profile("kimi", "balanced")
    kimi_max = resolve_effort_profile("kimi", "max")
    openai_fast = resolve_effort_profile("openai", "fast")
    openai_balanced = resolve_effort_profile("openai", "balanced")
    openai_max = resolve_effort_profile("openai", "max")

    assert deepseek_fast.capability.model_id == "deepseek-v4-flash"
    assert deepseek_fast.provider_parameters == {"thinking": "disabled"}
    assert deepseek_balanced.provider_parameters == {"thinking": "enabled"}
    assert deepseek_max.capability.model_id == "deepseek-v4-pro"
    assert kimi_fast.provider_parameters == {"reasoning_effort": "low"}
    assert kimi_balanced.provider_parameters == {"reasoning_effort": "high"}
    assert kimi_max.provider_parameters == {"reasoning_effort": "max"}
    assert openai_fast.capability.model_id == "gpt-5.6-luna"
    assert openai_balanced.capability.model_id == "gpt-5.6-terra"
    assert openai_max.capability.model_id == "gpt-5.6-sol"
    assert openai_max.provider_parameters == {"reasoning": {"effort": "max"}}


def test_unknown_provider_fails_closed() -> None:
    assert resolve_effort_profile("unknown", "balanced") is None
