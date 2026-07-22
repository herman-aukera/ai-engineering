"""Verified provider capability overlay for EACODE.

The legacy registry remains available for compatibility. Product-facing routing and
live adapters use this overlay so mutable provider facts have explicit source,
verification date, units, and conservative entitlement assumptions.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from energy_core.provider_registry import (
    CapabilityRegistry,
    ModelCapability,
    PricingSnapshot,
    ProviderSelector,
    _build_default_registry,
)

VERIFIED_AT = datetime(2026, 7, 22)
SOURCE_VERSION = "2026-07-22"


def _pricing(
    input_per_million: str,
    cached_per_million: str,
    output_per_million: str,
) -> PricingSnapshot:
    """Convert official per-million prices to the registry's per-1K fields."""

    divisor = Decimal("1000")
    return PricingSnapshot(
        input_price_per_1k_tokens=Decimal(input_per_million) / divisor,
        cached_input_price_per_1k_tokens=Decimal(cached_per_million) / divisor,
        output_price_per_1k_tokens=Decimal(output_per_million) / divisor,
        price_unit="per_1K_tokens",
    )


def build_verified_capabilities() -> dict[str, ModelCapability]:
    """Return a fresh capability map with current, source-bound provider facts."""

    capabilities = _build_default_registry()

    corrections: dict[str, dict[str, object]] = {
        "deepseek-v4-flash": {
            "pricing": _pricing("0.14", "0.0028", "0.28"),
            "source_id": "deepseek-official-pricing-and-thinking-mode",
            "source_version": SOURCE_VERSION,
            "verified_at": VERIFIED_AT,
            "freshness_state": "current",
        },
        "deepseek-v4-pro": {
            "pricing": _pricing("0.435", "0.003625", "0.87"),
            "source_id": "deepseek-official-pricing-and-thinking-mode",
            "source_version": SOURCE_VERSION,
            "verified_at": VERIFIED_AT,
            "freshness_state": "current",
        },
        "k3": {
            # Moderato-safe default. Higher entitlements may authorize 1M separately.
            "context_window": 262_144,
            "reasoning_efforts": ("low", "high", "max"),
            "source_id": "kimi-code-official-model-configuration",
            "source_version": SOURCE_VERSION,
            "verified_at": VERIFIED_AT,
            "freshness_state": "current",
        },
        "kimi-for-coding": {
            "context_window": 262_144,
            "reasoning_modes": ("thinking",),
            "reasoning_efforts": (),
            "source_id": "kimi-code-official-model-configuration",
            "source_version": SOURCE_VERSION,
            "verified_at": VERIFIED_AT,
            "freshness_state": "current",
        },
        "kimi-for-coding-highspeed": {
            "context_window": 262_144,
            "reasoning_modes": ("thinking",),
            "reasoning_efforts": (),
            "source_id": "kimi-code-official-model-configuration",
            "source_version": SOURCE_VERSION,
            "verified_at": VERIFIED_AT,
            "freshness_state": "current",
        },
        "gpt-5.6-luna": {
            "pricing": _pricing("1.00", "0.10", "6.00"),
            "source_id": "openai-official-gpt-5.6-model-catalog",
            "source_version": SOURCE_VERSION,
            "verified_at": VERIFIED_AT,
            "freshness_state": "current",
        },
        "gpt-5.6-terra": {
            "pricing": _pricing("2.50", "0.25", "15.00"),
            "source_id": "openai-official-gpt-5.6-model-catalog",
            "source_version": SOURCE_VERSION,
            "verified_at": VERIFIED_AT,
            "freshness_state": "current",
        },
        "gpt-5.6-sol": {
            "pricing": _pricing("5.00", "0.50", "30.00"),
            "source_id": "openai-official-gpt-5.6-model-catalog",
            "source_version": SOURCE_VERSION,
            "verified_at": VERIFIED_AT,
            "freshness_state": "current",
        },
    }

    for model_id, update in corrections.items():
        capability = capabilities.get(model_id)
        if capability is not None:
            capabilities[model_id] = capability.model_copy(update=update)

    # The general Kimi platform entry is not the Kimi Code membership surface.
    platform_k3 = capabilities.get("kimi-k3")
    if platform_k3 is not None:
        capabilities["kimi-k3"] = platform_k3.model_copy(
            update={
                "freshness_state": "unverified",
                "source_id": "kimi-platform-facts-require-separate-verification",
                "source_version": SOURCE_VERSION,
                "verified_at": VERIFIED_AT,
            }
        )

    return capabilities


class VerifiedCapabilityRegistry(CapabilityRegistry):
    """Capability registry whose defaults are the verified overlay."""

    def __init__(self, capabilities: dict[str, ModelCapability] | None = None) -> None:
        super().__init__(
            build_verified_capabilities() if capabilities is None else capabilities
        )


class VerifiedProviderSelector(ProviderSelector):
    """Provider selector backed by verified capability defaults."""

    def __init__(self, registry: CapabilityRegistry | None = None) -> None:
        super().__init__(registry or VerifiedCapabilityRegistry())
