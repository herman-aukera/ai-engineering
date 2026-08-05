"""Provider catalog facts, surfaces, effort resolution, and claim boundaries."""

from __future__ import annotations

from app.energy_chat.provider_catalog import (
    CATALOG_VERSION,
    DEEPSEEK_V4_FLASH,
    DEEPSEEK_V4_PRO,
    GPT56_LUNA,
    GPT56_SOL,
    GPT56_TERRA,
    KIMI_CODE_K3,
    KIMI_CODE_K27,
    KIMI_K3_PLATFORM,
    get_catalog,
    get_provider_models,
    resolve_effort_profile,
)


def test_deepseek_catalog_uses_current_verified_limits_and_prices() -> None:
    assert CATALOG_VERSION == "2.0.0"
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

    assert KIMI_CODE_K3.model_id == "k3"
    assert KIMI_CODE_K3.api_surface == "kimi_code_anthropic_compatible"
    assert KIMI_CODE_K3.eligible_for_eachat is False
    assert KIMI_CODE_K3.billing_model == "membership_quota"
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


def test_openai_preview_records_do_not_guess_unpublished_limits() -> None:
    assert [GPT56_LUNA.model_id, GPT56_TERRA.model_id, GPT56_SOL.model_id] == [
        "gpt-5.6-luna",
        "gpt-5.6-terra",
        "gpt-5.6-sol",
    ]
    assert GPT56_LUNA.context_window_tokens is None
    assert GPT56_TERRA.max_output_tokens is None
    assert GPT56_SOL.context_window_tokens is None
    assert GPT56_LUNA.input_price_per_million == 1.0
    assert GPT56_TERRA.input_price_per_million == 2.5
    assert GPT56_SOL.input_price_per_million == 5.0


def test_catalog_entries_are_source_dated_and_surface_specific() -> None:
    catalog = get_catalog()
    for provider_models in catalog.values():
        for model in provider_models.values():
            assert model.source_refs
            assert model.verified_at == "2026-07-21"
            assert model.api_surface
            assert model.endpoint_base_url.startswith("https://")
            assert model.billing_model
            assert model.adapter_status
            assert model.calibration_status


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
