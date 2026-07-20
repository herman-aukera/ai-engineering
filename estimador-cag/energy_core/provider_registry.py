"""Provider capability registry and selector for EACODE.

Provider-neutral model selection behind fake adapters in deterministic CI.
No live API calls. No provider keys required. Resolves provider/profile
combinations through a versioned capability manifest.

Spec 0010 runtime — additive module. Does not modify existing contracts.

Rescue audit R3 repairs applied (2026-07-20):
- Empty registry stays empty; no silent default fallback.
- Immutable registry instances; no shared mutable module state.
- Capability records carry source_id, source_version, price_unit, aliases,
  entitlement_state, and freshness_state.
- Budget enforced across all providers using explicit token assumptions.
- ProviderSelection carries expected_input/output/cached_input tokens.
- ResolvedProvider carries resolved_surface.
- Capability facts refreshed: DeepSeek 1M context + cache, Kimi K3 low/high/max,
  Kimi Code 262K context, GPT-5.6 1,050K context, Kimi Code surface distinction.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from energy_core.models import EnergyModel

ProviderName = Literal["auto", "deepseek", "kimi", "openai"]
Profile = Literal["minimal", "medium", "max"]
FallbackPolicy = Literal["none", "same_provider", "governed_cross_provider"]
AvailabilityState = Literal["available", "degraded", "unavailable"]
EntitlementState = Literal["open", "membership_required", "entitled_only", "unknown"]
FreshnessState = Literal["current", "stale", "unverified"]


class PricingSnapshot(EnergyModel):
    input_price_per_1k_tokens: Decimal = Field(default=Decimal("0.0"), ge=0)
    cached_input_price_per_1k_tokens: Decimal = Field(default=Decimal("0.0"), ge=0)
    output_price_per_1k_tokens: Decimal = Field(default=Decimal("0.0"), ge=0)
    price_unit: str = Field(default="per_1M_tokens")


class ModelCapability(EnergyModel):
    """Versioned capability entry for one provider model.

    Each entry records the exact surface, verified-at timestamp, source identity,
    and current freshness. Unknown/unsupported capabilities fail closed.
    """

    provider: str = Field(min_length=1, max_length=80)
    surface: str = Field(default="api", min_length=1, max_length=80)
    model_id: str = Field(min_length=1, max_length=160)
    aliases: tuple[str, ...] = Field(default_factory=tuple)
    model_family: str = Field(min_length=1, max_length=160)
    context_window: int = Field(ge=1)
    max_output_tokens: int = Field(ge=1)
    reasoning_modes: tuple[str, ...] = Field(default_factory=tuple)
    reasoning_efforts: tuple[str, ...] = Field(default_factory=tuple)
    speed_class: str = Field(default="medium")
    supports_tools: bool = False
    supports_structured_output: bool = False
    supports_vision: bool = False
    supports_prompt_cache: bool = False
    pricing: PricingSnapshot = Field(default_factory=PricingSnapshot)
    availability_state: AvailabilityState = "available"
    entitlement_state: EntitlementState = "open"
    verified_at: datetime = Field(default_factory=lambda: datetime(2026, 7, 19))
    source_id: str = Field(default="")
    source_version: str = Field(default="1.0.0")
    freshness_state: FreshnessState = "current"


class ProviderSelection(EnergyModel):
    """Provider-neutral model selection request with explicit token assumptions."""

    provider: ProviderName = "auto"
    profile: Profile = "medium"
    context_profile: Profile = "medium"
    fallback_policy: FallbackPolicy = "none"
    expected_input_tokens: int = Field(default=50_000, ge=1)
    expected_cached_input_tokens: int = Field(default=0, ge=0)
    expected_output_tokens: int = Field(default=4_000, ge=1)
    max_cost_usd: Decimal = Field(default=Decimal("1.00"), ge=0)
    max_latency_ms: int | None = None
    premium_reason: str | None = None


class ResolvedProvider(EnergyModel):
    """Deterministically resolved provider/model/effort result.

    This is a planned route, not proof of the model actually served.
    Served-model evidence requires a live provider response.
    """

    provider: str
    resolved_surface: str = ""
    model_id: str
    reasoning_mode: str
    reasoning_effort: str
    profile: Profile
    estimated_cost_ceiling_usd: Decimal
    capability_snapshot_hash: str
    fallback_used: bool = False
    fallback_reason: str | None = None


# ------------------------------------------------------------------
# Immutable curated capability fixtures
# ------------------------------------------------------------------


def _build_default_capabilities() -> dict[str, ModelCapability]:
    """Build the curated capability manifest from verified provider documentation.

    Returns a NEW dict every call. No shared mutable module state.
    Fact-based entries only. No invented capabilities.
    """

    return {
        # --- DeepSeek API ---
        "deepseek-v4-flash": ModelCapability(
            provider="deepseek",
            surface="deepseek_api",
            model_id="deepseek-v4-flash",
            model_family="deepseek-v4",
            context_window=1_000_000,
            max_output_tokens=384_000,
            reasoning_modes=("thinking", "non-thinking"),
            reasoning_efforts=("high", "max"),
            speed_class="fast",
            supports_tools=True,
            supports_structured_output=True,
            supports_prompt_cache=True,
            pricing=PricingSnapshot(
                input_price_per_1k_tokens=Decimal("0.00014"),
                cached_input_price_per_1k_tokens=Decimal("0.000014"),
                output_price_per_1k_tokens=Decimal("0.00028"),
                price_unit="per_1M_tokens",
            ),
            verified_at=datetime(2026, 7, 20),
            source_id="deepseek-api-docs-2026-07",
            source_version="2026-07-20",
        ),
        "deepseek-v4-pro": ModelCapability(
            provider="deepseek",
            surface="deepseek_api",
            model_id="deepseek-v4-pro",
            model_family="deepseek-v4",
            context_window=1_000_000,
            max_output_tokens=384_000,
            reasoning_modes=("thinking", "non-thinking"),
            reasoning_efforts=("high", "max"),
            speed_class="balanced",
            supports_tools=True,
            supports_structured_output=True,
            supports_prompt_cache=True,
            pricing=PricingSnapshot(
                input_price_per_1k_tokens=Decimal("0.00055"),
                cached_input_price_per_1k_tokens=Decimal("0.000055"),
                output_price_per_1k_tokens=Decimal("0.00219"),
                price_unit="per_1M_tokens",
            ),
            verified_at=datetime(2026, 7, 20),
            source_id="deepseek-api-docs-2026-07",
            source_version="2026-07-20",
        ),

        # --- Kimi general API ---
        "kimi-k3": ModelCapability(
            provider="kimi",
            surface="kimi_platform_api",
            model_id="kimi-k3",
            model_family="kimi-k3",
            context_window=1_000_000,
            max_output_tokens=8_192,
            reasoning_modes=("thinking",),
            reasoning_efforts=("max",),
            speed_class="balanced",
            supports_tools=True,
            supports_structured_output=True,
            supports_vision=True,
            supports_prompt_cache=False,
            pricing=PricingSnapshot(
                input_price_per_1k_tokens=Decimal("0.00060"),
                output_price_per_1k_tokens=Decimal("0.00240"),
                price_unit="per_1M_tokens",
            ),
            verified_at=datetime(2026, 7, 20),
            source_id="kimi-platform-docs-2026-07",
            source_version="2026-07-20",
        ),

        # --- Kimi Code ---
        "k3": ModelCapability(
            provider="kimi",
            surface="kimi_code",
            model_id="k3",
            aliases=("kimi-k3",),
            model_family="kimi-k3",
            context_window=1_048_576,
            max_output_tokens=8_192,
            reasoning_modes=("thinking",),
            reasoning_efforts=("low", "high", "max"),
            speed_class="balanced",
            supports_tools=True,
            supports_structured_output=True,
            supports_vision=True,
            supports_prompt_cache=False,
            pricing=PricingSnapshot(
                input_price_per_1k_tokens=Decimal("0.00000"),
                output_price_per_1k_tokens=Decimal("0.00000"),
                price_unit="per_1M_tokens",
            ),
            entitlement_state="membership_required",
            verified_at=datetime(2026, 7, 20),
            source_id="kimi-code-docs-2026-07",
            source_version="2026-07-20",
        ),
        "kimi-for-coding": ModelCapability(
            provider="kimi",
            surface="kimi_code",
            model_id="kimi-for-coding",
            aliases=(),
            model_family="kimi-k2.7-code",
            context_window=262_144,
            max_output_tokens=8_192,
            reasoning_modes=("thinking", "non-thinking"),
            reasoning_efforts=("low", "medium", "high"),
            speed_class="fast",
            supports_tools=True,
            supports_structured_output=True,
            supports_vision=False,
            supports_prompt_cache=False,
            pricing=PricingSnapshot(
                input_price_per_1k_tokens=Decimal("0.00000"),
                output_price_per_1k_tokens=Decimal("0.00000"),
                price_unit="per_1M_tokens",
            ),
            entitlement_state="membership_required",
            verified_at=datetime(2026, 7, 20),
            source_id="kimi-code-docs-2026-07",
            source_version="2026-07-20",
        ),
        "kimi-for-coding-highspeed": ModelCapability(
            provider="kimi",
            surface="kimi_code",
            model_id="kimi-for-coding-highspeed",
            aliases=(),
            model_family="kimi-k2.7-code-highspeed",
            context_window=262_144,
            max_output_tokens=8_192,
            reasoning_modes=("thinking", "non-thinking"),
            reasoning_efforts=("low", "medium", "high"),
            speed_class="fast",
            supports_tools=True,
            supports_structured_output=True,
            supports_vision=False,
            supports_prompt_cache=False,
            pricing=PricingSnapshot(
                input_price_per_1k_tokens=Decimal("0.00000"),
                output_price_per_1k_tokens=Decimal("0.00000"),
                price_unit="per_1M_tokens",
            ),
            entitlement_state="membership_required",
            verified_at=datetime(2026, 7, 20),
            source_id="kimi-code-docs-2026-07",
            source_version="2026-07-20",
        ),

        # --- OpenAI API ---
        "gpt-5.6-luna": ModelCapability(
            provider="openai",
            surface="openai_api",
            model_id="gpt-5.6-luna",
            model_family="gpt-5.6",
            context_window=1_050_000,
            max_output_tokens=128_000,
            reasoning_modes=("thinking", "non-thinking"),
            reasoning_efforts=("none", "low", "medium", "high", "xhigh", "max"),
            speed_class="fast",
            supports_tools=True,
            supports_structured_output=True,
            supports_vision=True,
            supports_prompt_cache=True,
            pricing=PricingSnapshot(
                input_price_per_1k_tokens=Decimal("0.00015"),
                cached_input_price_per_1k_tokens=Decimal("0.00008"),
                output_price_per_1k_tokens=Decimal("0.00060"),
                price_unit="per_1M_tokens",
            ),
            verified_at=datetime(2026, 7, 20),
            source_id="openai-api-docs-2026-07",
            source_version="2026-07-20",
        ),
        "gpt-5.6-terra": ModelCapability(
            provider="openai",
            surface="openai_api",
            model_id="gpt-5.6-terra",
            model_family="gpt-5.6",
            context_window=1_050_000,
            max_output_tokens=128_000,
            reasoning_modes=("thinking", "non-thinking"),
            reasoning_efforts=("none", "low", "medium", "high", "xhigh", "max"),
            speed_class="balanced",
            supports_tools=True,
            supports_structured_output=True,
            supports_vision=True,
            supports_prompt_cache=True,
            pricing=PricingSnapshot(
                input_price_per_1k_tokens=Decimal("0.00150"),
                cached_input_price_per_1k_tokens=Decimal("0.00075"),
                output_price_per_1k_tokens=Decimal("0.00600"),
                price_unit="per_1M_tokens",
            ),
            verified_at=datetime(2026, 7, 20),
            source_id="openai-api-docs-2026-07",
            source_version="2026-07-20",
        ),
        "gpt-5.6-sol": ModelCapability(
            provider="openai",
            surface="openai_api",
            model_id="gpt-5.6-sol",
            model_family="gpt-5.6",
            context_window=1_050_000,
            max_output_tokens=128_000,
            reasoning_modes=("thinking", "non-thinking"),
            reasoning_efforts=("none", "low", "medium", "high", "xhigh", "max"),
            speed_class="premium",
            supports_tools=True,
            supports_structured_output=True,
            supports_vision=True,
            supports_prompt_cache=True,
            pricing=PricingSnapshot(
                input_price_per_1k_tokens=Decimal("0.00300"),
                cached_input_price_per_1k_tokens=Decimal("0.00150"),
                output_price_per_1k_tokens=Decimal("0.01200"),
                price_unit="per_1M_tokens",
            ),
            verified_at=datetime(2026, 7, 20),
            source_id="openai-api-docs-2026-07",
            source_version="2026-07-20",
        ),
    }


# ------------------------------------------------------------------
# Profile-to-model mapping (deterministic)
# ------------------------------------------------------------------

_PROFILE_MAP: dict[tuple[str, Profile], str] = {
    ("deepseek", "minimal"): "deepseek-v4-flash",
    ("deepseek", "medium"): "deepseek-v4-flash",
    ("deepseek", "max"): "deepseek-v4-pro",
    ("kimi", "minimal"): "kimi-for-coding",
    ("kimi", "medium"): "k3",
    ("kimi", "max"): "k3",
    ("openai", "minimal"): "gpt-5.6-luna",
    ("openai", "medium"): "gpt-5.6-terra",
    ("openai", "max"): "gpt-5.6-sol",
}

_EFFORT_MAP: dict[tuple[str, Profile], str] = {
    ("deepseek", "minimal"): "high",
    ("deepseek", "medium"): "high",
    ("deepseek", "max"): "max",
    ("kimi", "minimal"): "low",
    ("kimi", "medium"): "high",
    ("kimi", "max"): "max",
    ("openai", "minimal"): "low",
    ("openai", "medium"): "medium",
    ("openai", "max"): "max",
}

_MODE_MAP: dict[tuple[str, Profile], str] = {
    ("deepseek", "minimal"): "non-thinking",
    ("deepseek", "medium"): "thinking",
    ("deepseek", "max"): "thinking",
    ("kimi", "minimal"): "thinking",
    ("kimi", "medium"): "thinking",
    ("kimi", "max"): "thinking",
    ("openai", "minimal"): "non-thinking",
    ("openai", "medium"): "thinking",
    ("openai", "max"): "thinking",
}

_DEFAULT_PROVIDER = "deepseek"

_FALLBACK_ORDER: dict[str, list[str]] = {
    "deepseek": ["kimi", "openai"],
    "kimi": ["deepseek", "openai"],
    "openai": ["deepseek", "kimi"],
}


# ------------------------------------------------------------------
# Capability registry
# ------------------------------------------------------------------


class CapabilityRegistry:
    """Versioned capability registry with deterministic resolution.

    Does not call any live API. Capabilities are curated from verified
    provider documentation. Unknown or unsupported combinations fail closed.

    An explicitly empty dict stays empty — no silent default fallback.
    A None argument loads the built-in curated defaults.
    """

    def __init__(self, capabilities: dict[str, ModelCapability] | None = None) -> None:
        if capabilities is None:
            self._capabilities = _build_default_capabilities()
        else:
            self._capabilities = dict(capabilities)  # defensive copy

    def get(self, model_id: str) -> ModelCapability | None:
        """Get one capability entry by model_id. Returns None if unknown."""
        return self._capabilities.get(model_id)

    def list_provider_models(self, provider: str) -> list[ModelCapability]:
        """List all registered capability entries for a provider."""
        return sorted(
            (c for c in self._capabilities.values() if c.provider == provider),
            key=lambda c: c.model_id,
        )

    def list_available_models(self) -> list[ModelCapability]:
        """List all registered models with availability_state=available."""
        return sorted(
            (c for c in self._capabilities.values()
             if c.availability_state == "available"),
            key=lambda c: (c.provider, c.model_id),
        )

    # ------------------------------------------------------------------
    # Profile resolution
    # ------------------------------------------------------------------

    def resolve_profile(
        self,
        provider: str,
        profile: Profile,
    ) -> tuple[str, str, str]:
        """Resolve provider+profile to (model_id, reasoning_mode, reasoning_effort).

        Raises ValueError if the combination is unsupported.
        """
        key = (provider, profile)
        model_id = _PROFILE_MAP.get(key)
        if model_id is None:
            raise ValueError(
                f"Unsupported provider/profile combination: {provider}/{profile}"
            )

        cap = self.get(model_id)
        if cap is None or cap.availability_state == "unavailable":
            raise ValueError(
                f"Model {model_id} is unavailable for provider {provider}"
            )

        effort = _EFFORT_MAP.get(key, "medium")
        mode = _MODE_MAP.get(key, "thinking")

        if effort not in cap.reasoning_efforts:
            raise ValueError(
                f"Effort '{effort}' not supported by {model_id}. "
                f"Supported: {cap.reasoning_efforts}"
            )

        if mode not in cap.reasoning_modes and cap.reasoning_modes:
            raise ValueError(
                f"Mode '{mode}' not supported by {model_id}. "
                f"Supported: {cap.reasoning_modes}"
            )

        return model_id, mode, effort


# ------------------------------------------------------------------
# Provider selector
# ------------------------------------------------------------------


class ProviderSelector:
    """Deterministic provider selector with budget-aware auto-routing.

    Does not make live API calls. Produces a ResolvedProvider from a
    ProviderSelection using the capability registry.

    Budget enforcement applies to every provider using explicit token assumptions.
    OpenAI additionally requires premium_reason for max/escalation profiles.
    """

    def __init__(self, registry: CapabilityRegistry | None = None) -> None:
        self._registry = registry or CapabilityRegistry()

    def select(self, selection: ProviderSelection) -> ResolvedProvider:
        """Resolve a ProviderSelection to a specific model/effort.

        In 'auto' mode, follows the default routing policy:
        1. DeepSeek for normal cost-sensitive work
        2. Kimi for quality-sensitive / open-frontier preference
        3. OpenAI only for explicit premium escalation
        """
        provider = selection.provider
        fallback_used = False
        fallback_reason: str | None = None

        if provider == "auto":
            provider = _DEFAULT_PROVIDER

        if provider == "openai" and selection.profile == "max" and not selection.premium_reason:
            raise ValueError(
                "OpenAI max/escalation requires explicit premium_reason"
            )

        try:
            model_id, mode, effort = self._registry.resolve_profile(
                provider, selection.profile
            )
        except ValueError:
            if selection.fallback_policy == "none":
                raise
            if selection.fallback_policy == "same_provider":
                raise ValueError(
                    f"Cannot resolve {provider}/{selection.profile} "
                    "and fallback_policy=same_provider"
                )
            fallback_order = _FALLBACK_ORDER.get(provider, [_DEFAULT_PROVIDER])
            resolved = False
            for fb_provider in fallback_order:
                try:
                    model_id, mode, effort = self._registry.resolve_profile(
                        fb_provider, selection.profile
                    )
                    provider = fb_provider
                    fallback_used = True
                    fallback_reason = (
                        f"Primary provider {selection.provider} could not resolve "
                        f"profile {selection.profile}; fell back to {fb_provider}"
                    )
                    resolved = True
                    break
                except ValueError:
                    continue
            if not resolved:
                raise ValueError(
                    f"Cannot resolve any provider for profile {selection.profile}"
                )

        # Budget enforcement: applies to every provider
        cap = self._registry.get(model_id)
        if cap is not None:
            uncached = max(0, selection.expected_input_tokens - selection.expected_cached_input_tokens)
            cached = selection.expected_cached_input_tokens
            est_cost = (
                Decimal(str(uncached)) * cap.pricing.input_price_per_1k_tokens
                + Decimal(str(cached)) * cap.pricing.cached_input_price_per_1k_tokens
                + Decimal(str(selection.expected_output_tokens)) * cap.pricing.output_price_per_1k_tokens
            ) / 1000  # prices are per-1k tokens

            if est_cost > selection.max_cost_usd:
                raise ValueError(
                    f"Estimated cost ${est_cost:.6f} exceeds budget "
                    f"${selection.max_cost_usd:.6f} for {provider}/{model_id}"
                )

        # Surface from capability
        surface = cap.surface if cap else ""

        cap_hash = _sha256_json({
            "provider": provider,
            "surface": surface,
            "model_id": model_id,
            "mode": mode,
            "effort": effort,
            "profile": selection.profile,
        })

        return ResolvedProvider(
            provider=provider,
            resolved_surface=surface,
            model_id=model_id,
            reasoning_mode=mode,
            reasoning_effort=effort,
            profile=selection.profile,
            estimated_cost_ceiling_usd=selection.max_cost_usd,
            capability_snapshot_hash=cap_hash,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        )


def _sha256_json(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


# Legacy alias for backward compatibility with existing tests
def _build_default_registry() -> dict[str, ModelCapability]:
    return _build_default_capabilities()
