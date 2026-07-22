"""Versioned provider/model capability catalog for Energy Aware Chat.

Every temporal fact is source-dated. Product API surfaces are distinct from
coding-agent membership surfaces, and unknown limits remain ``None`` rather
than being guessed.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CATALOG_VERSION = "2.0.0"
CATALOG_VERIFIED_AT = "2026-07-21"

ProviderName = Literal["deepseek", "kimi", "openai"]
EffortProfile = Literal["fast", "balanced", "max"]
AvailabilityStatus = Literal["verified", "preview", "documented", "restricted"]
AdapterStatus = Literal[
    "implemented_live_unproven",
    "catalog_only",
    "coding_surface_only",
]
CalibrationStatus = Literal["deterministic_mapping", "uncalibrated"]
BillingModel = Literal["pay_as_you_go", "membership_quota"]


class ProviderModelCapability(BaseModel):
    """One allow-listed provider model on one explicit API surface."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    catalog_version: Literal["2.0.0"] = CATALOG_VERSION
    provider: ProviderName
    api_surface: str = Field(min_length=1)
    endpoint_base_url: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    availability_status: AvailabilityStatus
    verified_at: str = CATALOG_VERIFIED_AT
    source_refs: list[str] = Field(min_length=1)
    context_window_tokens: int | None = Field(default=None, ge=1)
    max_output_tokens: int | None = Field(default=None, ge=1)
    modalities: list[str] = Field(default_factory=lambda: ["text"])
    supports_tools: bool = False
    supports_structured_output: bool = False
    supports_streaming: bool = True
    supports_prompt_caching: bool = False
    supported_effort_profiles: list[EffortProfile] = Field(default_factory=list)
    provider_reasoning_values: list[str] = Field(default_factory=list)
    input_price_per_million: float | None = Field(default=None, ge=0.0)
    cached_input_price_per_million: float | None = Field(default=None, ge=0.0)
    output_price_per_million: float | None = Field(default=None, ge=0.0)
    billing_model: BillingModel
    adapter_status: AdapterStatus
    calibration_status: CalibrationStatus = "uncalibrated"
    eligible_for_eachat: bool = True
    entitlement_notes: str | None = None


class ResolvedProviderProfile(BaseModel):
    """Deterministic mapping from stable product effort to provider parameters."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: ProviderName
    effort_profile: EffortProfile
    capability: ProviderModelCapability
    provider_parameters: dict[str, object] = Field(default_factory=dict)
    routing_reason: str = Field(min_length=1)


_DEEPSEEK_SOURCE = "https://api-docs.deepseek.com/quick_start/pricing"
_KIMI_PLATFORM_SOURCE = "https://platform.kimi.ai/docs/guide/kimi-k3-quickstart"
_KIMI_CODE_SOURCE = "https://www.kimi.com/code/docs/en/kimi-code/models.html"
_OPENAI_RELEASE_SOURCE = "https://openai.com/index/gpt-5-6/"
_OPENAI_HELP_SOURCE = "https://help.openai.com/en/articles/20001354-gpt-56-in-chatgpt"

DEEPSEEK_V4_FLASH = ProviderModelCapability(
    provider="deepseek",
    api_surface="deepseek_openai_compatible",
    endpoint_base_url="https://api.deepseek.com",
    model_id="deepseek-v4-flash",
    display_name="DeepSeek V4 Flash",
    availability_status="verified",
    source_refs=[_DEEPSEEK_SOURCE],
    context_window_tokens=1_000_000,
    max_output_tokens=384_000,
    supports_tools=True,
    supports_structured_output=True,
    supports_streaming=True,
    supports_prompt_caching=True,
    supported_effort_profiles=["fast", "balanced"],
    provider_reasoning_values=["disabled", "enabled"],
    input_price_per_million=0.14,
    cached_input_price_per_million=0.0028,
    output_price_per_million=0.28,
    billing_model="pay_as_you_go",
    adapter_status="implemented_live_unproven",
    calibration_status="deterministic_mapping",
)

DEEPSEEK_V4_PRO = ProviderModelCapability(
    provider="deepseek",
    api_surface="deepseek_openai_compatible",
    endpoint_base_url="https://api.deepseek.com",
    model_id="deepseek-v4-pro",
    display_name="DeepSeek V4 Pro",
    availability_status="verified",
    source_refs=[_DEEPSEEK_SOURCE],
    context_window_tokens=1_000_000,
    max_output_tokens=384_000,
    supports_tools=True,
    supports_structured_output=True,
    supports_streaming=True,
    supports_prompt_caching=True,
    supported_effort_profiles=["balanced", "max"],
    provider_reasoning_values=["disabled", "enabled"],
    input_price_per_million=0.435,
    cached_input_price_per_million=0.003625,
    output_price_per_million=0.87,
    billing_model="pay_as_you_go",
    adapter_status="implemented_live_unproven",
    calibration_status="deterministic_mapping",
)

KIMI_K3_PLATFORM = ProviderModelCapability(
    provider="kimi",
    api_surface="kimi_platform_openai_compatible",
    endpoint_base_url="https://api.moonshot.ai/v1",
    model_id="kimi-k3",
    display_name="Kimi K3",
    availability_status="verified",
    source_refs=[_KIMI_PLATFORM_SOURCE],
    context_window_tokens=1_000_000,
    max_output_tokens=1_048_576,
    modalities=["text", "image", "video"],
    supports_tools=True,
    supports_structured_output=True,
    supports_streaming=True,
    supports_prompt_caching=True,
    supported_effort_profiles=["fast", "balanced", "max"],
    provider_reasoning_values=["low", "high", "max"],
    input_price_per_million=3.00,
    cached_input_price_per_million=0.30,
    output_price_per_million=15.00,
    billing_model="pay_as_you_go",
    adapter_status="implemented_live_unproven",
    calibration_status="deterministic_mapping",
    entitlement_notes="Requires a successful Kimi API Platform top-up of at least USD 1.",
)

KIMI_CODE_K3 = ProviderModelCapability(
    provider="kimi",
    api_surface="kimi_code_anthropic_compatible",
    endpoint_base_url="https://api.kimi.com/coding/",
    model_id="k3",
    display_name="Kimi K3 for Kimi Code",
    availability_status="restricted",
    source_refs=[_KIMI_CODE_SOURCE],
    context_window_tokens=1_000_000,
    max_output_tokens=None,
    supports_tools=True,
    supports_structured_output=False,
    supports_streaming=True,
    supports_prompt_caching=True,
    supported_effort_profiles=["fast", "balanced", "max"],
    provider_reasoning_values=["low", "high", "max"],
    billing_model="membership_quota",
    adapter_status="coding_surface_only",
    eligible_for_eachat=False,
    entitlement_notes="Kimi Code membership surface; not an EACHAT product-runtime credential.",
)

KIMI_CODE_K27 = ProviderModelCapability(
    provider="kimi",
    api_surface="kimi_code_anthropic_compatible",
    endpoint_base_url="https://api.kimi.com/coding/",
    model_id="kimi-for-coding",
    display_name="Kimi K2.7 Code",
    availability_status="restricted",
    source_refs=[_KIMI_CODE_SOURCE],
    context_window_tokens=256_000,
    max_output_tokens=None,
    modalities=["text", "image", "video"],
    supports_tools=True,
    supports_structured_output=False,
    supports_streaming=True,
    supports_prompt_caching=True,
    supported_effort_profiles=[],
    provider_reasoning_values=["thinking_always_on"],
    billing_model="membership_quota",
    adapter_status="coding_surface_only",
    eligible_for_eachat=False,
    entitlement_notes="Coding-agent membership model; thinking remains enabled.",
)

GPT56_LUNA = ProviderModelCapability(
    provider="openai",
    api_surface="openai_responses",
    endpoint_base_url="https://api.openai.com/v1",
    model_id="gpt-5.6-luna",
    display_name="GPT-5.6 Luna",
    availability_status="preview",
    source_refs=[_OPENAI_RELEASE_SOURCE, _OPENAI_HELP_SOURCE],
    context_window_tokens=None,
    max_output_tokens=None,
    supports_tools=True,
    supports_structured_output=True,
    supports_streaming=True,
    supports_prompt_caching=True,
    supported_effort_profiles=["fast"],
    provider_reasoning_values=[],
    input_price_per_million=1.00,
    output_price_per_million=6.00,
    billing_model="pay_as_you_go",
    adapter_status="implemented_live_unproven",
    calibration_status="deterministic_mapping",
    entitlement_notes="Preview availability; exact context/output limits are not published in the cited preview docs.",
)

GPT56_TERRA = ProviderModelCapability(
    provider="openai",
    api_surface="openai_responses",
    endpoint_base_url="https://api.openai.com/v1",
    model_id="gpt-5.6-terra",
    display_name="GPT-5.6 Terra",
    availability_status="preview",
    source_refs=[_OPENAI_RELEASE_SOURCE, _OPENAI_HELP_SOURCE],
    context_window_tokens=None,
    max_output_tokens=None,
    supports_tools=True,
    supports_structured_output=True,
    supports_streaming=True,
    supports_prompt_caching=True,
    supported_effort_profiles=["balanced"],
    provider_reasoning_values=[],
    input_price_per_million=2.50,
    output_price_per_million=15.00,
    billing_model="pay_as_you_go",
    adapter_status="implemented_live_unproven",
    calibration_status="deterministic_mapping",
    entitlement_notes="Preview availability; exact context/output limits are not published in the cited preview docs.",
)

GPT56_SOL = ProviderModelCapability(
    provider="openai",
    api_surface="openai_responses",
    endpoint_base_url="https://api.openai.com/v1",
    model_id="gpt-5.6-sol",
    display_name="GPT-5.6 Sol",
    availability_status="preview",
    source_refs=[_OPENAI_RELEASE_SOURCE, _OPENAI_HELP_SOURCE],
    context_window_tokens=None,
    max_output_tokens=None,
    supports_tools=True,
    supports_structured_output=True,
    supports_streaming=True,
    supports_prompt_caching=True,
    supported_effort_profiles=["max"],
    provider_reasoning_values=["max"],
    input_price_per_million=5.00,
    output_price_per_million=30.00,
    billing_model="pay_as_you_go",
    adapter_status="implemented_live_unproven",
    calibration_status="deterministic_mapping",
    entitlement_notes="Preview availability; exact context/output limits are not published in the cited preview docs.",
)

MODEL_CATALOG: tuple[ProviderModelCapability, ...] = (
    DEEPSEEK_V4_FLASH,
    DEEPSEEK_V4_PRO,
    KIMI_K3_PLATFORM,
    KIMI_CODE_K3,
    KIMI_CODE_K27,
    GPT56_LUNA,
    GPT56_TERRA,
    GPT56_SOL,
)
KIMI_K3 = KIMI_K3_PLATFORM


def get_catalog() -> dict[str, dict[str, ProviderModelCapability]]:
    catalog: dict[str, dict[str, ProviderModelCapability]] = {}
    for entry in MODEL_CATALOG:
        catalog.setdefault(entry.provider, {})[entry.model_id] = entry
    return catalog


def get_provider_models(
    provider: ProviderName,
    *,
    eachat_only: bool = True,
) -> list[ProviderModelCapability]:
    return [
        item
        for item in MODEL_CATALOG
        if item.provider == provider
        and (item.eligible_for_eachat or not eachat_only)
    ]


def resolve_effort_profile(
    provider: ProviderName,
    effort: EffortProfile,
    *,
    catalog: dict[str, dict[str, ProviderModelCapability]] | None = None,
) -> ResolvedProviderProfile | None:
    """Resolve one stable effort selector to an allow-listed product model."""

    del catalog  # custom v1 catalogs are no longer accepted by the strict v2 resolver
    if provider == "deepseek":
        if effort == "fast":
            return _profile(
                DEEPSEEK_V4_FLASH,
                effort,
                {"thinking": "disabled"},
                "Fast uses DeepSeek V4 Flash without thinking.",
            )
        if effort == "balanced":
            return _profile(
                DEEPSEEK_V4_FLASH,
                effort,
                {"thinking": "enabled"},
                "Balanced uses DeepSeek V4 Flash with thinking enabled.",
            )
        return _profile(
            DEEPSEEK_V4_PRO,
            effort,
            {"thinking": "enabled"},
            "Max uses DeepSeek V4 Pro with thinking enabled.",
        )
    if provider == "kimi":
        reasoning = {"fast": "low", "balanced": "high", "max": "max"}[effort]
        return _profile(
            KIMI_K3_PLATFORM,
            effort,
            {"reasoning_effort": reasoning},
            f"Kimi Platform K3 uses reasoning_effort={reasoning}.",
        )
    if provider == "openai":
        capability = {
            "fast": GPT56_LUNA,
            "balanced": GPT56_TERRA,
            "max": GPT56_SOL,
        }[effort]
        parameters: dict[str, object] = (
            {"reasoning": {"effort": "max"}} if effort == "max" else {}
        )
        return _profile(
            capability,
            effort,
            parameters,
            f"OpenAI {effort} maps to {capability.display_name}.",
        )
    return None


def _profile(
    capability: ProviderModelCapability,
    effort: EffortProfile,
    provider_parameters: dict[str, object],
    reason: str,
) -> ResolvedProviderProfile:
    return ResolvedProviderProfile(
        provider=capability.provider,
        effort_profile=effort,
        capability=capability,
        provider_parameters=provider_parameters,
        routing_reason=reason,
    )
