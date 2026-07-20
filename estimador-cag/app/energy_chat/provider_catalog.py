"""Provider capability catalog for Energy Aware Chat.

Milestone 17: versioned, allow-listed provider model records with source
references, verification dates, and capability facts. Unknown models fail
closed. No guessed IDs — every entry requires an official source reference.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ── Catalog types ───────────────────────────────────────────────────────

CatalogVersion = Literal["1.0.0"]
AvailabilityStatus = Literal["verified", "documented", "deprecated"]
SpeedClass = Literal["fast", "balanced", "premium"]
CostClass = Literal["low", "medium", "high"]


class ProviderModelCapability(BaseModel):
    """One versioned, source-referenced provider model record.

    Every field that is temporal (pricing, context window, availability) must
    record a verified_at date and a source_refs entry. Unknown or unverified
    values must be marked as such — never guessed.
    """

    catalog_version: CatalogVersion = "1.0.0"
    provider: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    availability_status: AvailabilityStatus
    verified_at: str = Field(min_length=1)
    context_window_tokens: int = Field(ge=1)
    max_output_tokens: int = Field(ge=1)
    modalities: list[str] = Field(default_factory=list)
    supports_tools: bool = False
    supports_structured_output: bool = False
    supports_streaming: bool = False
    supported_effort_profiles: list[str] = Field(default_factory=list)
    speed_class: SpeedClass = "balanced"
    cost_class: CostClass = "medium"
    input_price_per_million: float | None = None
    output_price_per_million: float | None = None
    data_handling_profile: str = "unknown"
    source_refs: list[str] = Field(default_factory=list, min_length=1)


# ── Catalog — current as of 2026-07-20 ─────────────────────────────────

DEEPSEEK_V4_FLASH = ProviderModelCapability(
    provider="deepseek",
    model_id="deepseek-v4-flash",
    display_name="DeepSeek V4 Flash",
    availability_status="verified",
    verified_at="2026-07-19",
    context_window_tokens=1_000_000,
    max_output_tokens=8_000,
    modalities=["text"],
    supports_tools=True,
    supports_structured_output=False,
    supports_streaming=True,
    supported_effort_profiles=["fast", "balanced"],
    speed_class="fast",
    cost_class="low",
    input_price_per_million=0.14,
    output_price_per_million=0.28,
    data_handling_profile="standard",
    source_refs=["https://api-docs.deepseek.com/quick_start/pricing"],
)

DEEPSEEK_V4_PRO = ProviderModelCapability(
    provider="deepseek",
    model_id="deepseek-v4-pro",
    display_name="DeepSeek V4 Pro",
    availability_status="verified",
    verified_at="2026-07-19",
    context_window_tokens=1_000_000,
    max_output_tokens=8_000,
    modalities=["text"],
    supports_tools=True,
    supports_structured_output=False,
    supports_streaming=True,
    supported_effort_profiles=["balanced", "max"],
    speed_class="balanced",
    cost_class="medium",
    input_price_per_million=0.55,
    output_price_per_million=2.19,
    data_handling_profile="standard",
    source_refs=["https://api-docs.deepseek.com/quick_start/pricing"],
)

KIMI_K3 = ProviderModelCapability(
    provider="kimi",
    model_id="kimi-k3-preview",
    display_name="Kimi K3",
    availability_status="documented",
    verified_at="2026-07-19",
    context_window_tokens=1_000_000,
    max_output_tokens=8_000,
    modalities=["text"],
    supports_tools=False,
    supports_structured_output=False,
    supports_streaming=False,
    supported_effort_profiles=[],
    speed_class="balanced",
    cost_class="medium",
    input_price_per_million=None,
    output_price_per_million=None,
    data_handling_profile="unknown",
    source_refs=["https://www.moonshot.ai/"],
)

GPT56_LUNA = ProviderModelCapability(
    provider="openai",
    model_id="gpt-5.6-luna",
    display_name="GPT-5.6 Luna",
    availability_status="documented",
    verified_at="2026-07-19",
    context_window_tokens=256_000,
    max_output_tokens=16_000,
    modalities=["text"],
    supports_tools=True,
    supports_structured_output=True,
    supports_streaming=True,
    supported_effort_profiles=["fast"],
    speed_class="fast",
    cost_class="medium",
    input_price_per_million=None,
    output_price_per_million=None,
    data_handling_profile="standard",
    source_refs=["https://openai.com/index/gpt-5-6/"],
)

GPT56_TERRA = ProviderModelCapability(
    provider="openai",
    model_id="gpt-5.6-terra",
    display_name="GPT-5.6 Terra",
    availability_status="documented",
    verified_at="2026-07-19",
    context_window_tokens=256_000,
    max_output_tokens=16_000,
    modalities=["text"],
    supports_tools=True,
    supports_structured_output=True,
    supports_streaming=True,
    supported_effort_profiles=["balanced"],
    speed_class="balanced",
    cost_class="medium",
    input_price_per_million=None,
    output_price_per_million=None,
    data_handling_profile="standard",
    source_refs=["https://openai.com/index/gpt-5-6/"],
)

GPT56_SOL = ProviderModelCapability(
    provider="openai",
    model_id="gpt-5.6-sol",
    display_name="GPT-5.6 Sol",
    availability_status="documented",
    verified_at="2026-07-19",
    context_window_tokens=256_000,
    max_output_tokens=32_000,
    modalities=["text"],
    supports_tools=True,
    supports_structured_output=True,
    supports_streaming=True,
    supported_effort_profiles=["max"],
    speed_class="premium",
    cost_class="high",
    input_price_per_million=None,
    output_price_per_million=None,
    data_handling_profile="standard",
    source_refs=["https://openai.com/index/gpt-5-6/"],
)


def get_catalog() -> dict[str, dict[str, ProviderModelCapability]]:
    """Return the current allow-listed provider catalog.

    Keyed by provider name, then by model_id. Only verified entries should
    be used for live provider routing. Documented entries require explicit
    account-visible API verification before enablement.
    """
    entries = [
        DEEPSEEK_V4_FLASH,
        DEEPSEEK_V4_PRO,
        KIMI_K3,
        GPT56_LUNA,
        GPT56_TERRA,
        GPT56_SOL,
    ]
    catalog: dict[str, dict[str, ProviderModelCapability]] = {}
    for entry in entries:
        catalog.setdefault(entry.provider, {})[entry.model_id] = entry
    return catalog


def resolve_effort_profile(
    provider: str,
    effort: str,
    *,
    catalog: dict[str, dict[str, ProviderModelCapability]] | None = None,
) -> ProviderModelCapability | None:
    """Find the cheapest verified model for a provider that supports the
    requested effort profile. Returns None when no compatible model exists.
    """
    models = (catalog or get_catalog()).get(provider, {})
    candidates = [
        m for m in models.values()
        if m.availability_status == "verified" and effort in m.supported_effort_profiles
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda m: (m.input_price_per_million or float("inf")))
    return candidates[0]
