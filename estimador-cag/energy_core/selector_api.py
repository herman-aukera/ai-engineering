"""Domain facade for deterministic provider selection.

Despite the historical module name, this is not a FastAPI router. The actual HTTP
surface is ``app.routers.eacode``. This facade remains for Python callers and uses
the verified capability overlay by default. It never makes a live provider call.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from energy_core.provider_registry import (
    CapabilityRegistry,
    ProviderSelection,
)
from energy_core.provider_verified import (
    VerifiedCapabilityRegistry,
    VerifiedProviderSelector,
)


class ModelSummary(BaseModel):
    provider: str
    surface: str
    model_id: str
    aliases: list[str]
    model_family: str
    context_window: int
    max_output_tokens: int
    reasoning_efforts: list[str]
    speed_class: str
    supports_prompt_cache: bool
    availability_state: str
    entitlement_state: str
    freshness_state: str


class ResolvedRoute(BaseModel):
    provider: str
    resolved_surface: str
    model_id: str
    reasoning_mode: str
    reasoning_effort: str
    profile: str
    capability_snapshot_hash: str
    fallback_used: bool
    fallback_reason: str | None


class SelectRequest(BaseModel):
    provider: str = "auto"
    profile: str = "medium"
    context_profile: str = "medium"
    fallback_policy: str = "none"
    expected_input_tokens: int = Field(default=50_000, ge=1)
    expected_cached_input_tokens: int = Field(default=0, ge=0)
    expected_output_tokens: int = Field(default=4_000, ge=1)
    max_cost_usd: Decimal = Field(default=Decimal("1.00"), ge=0)
    max_latency_ms: int | None = Field(default=None, ge=1)
    premium_reason: str | None = None


class SelectResponse(BaseModel):
    status: str
    route: ResolvedRoute | None = None
    available_models: list[ModelSummary] = Field(default_factory=list)
    error: str | None = None


class CapabilityDetail(BaseModel):
    provider: str
    surface: str
    model_id: str
    aliases: list[str]
    model_family: str
    context_window: int
    max_output_tokens: int
    reasoning_modes: list[str]
    reasoning_efforts: list[str]
    speed_class: str
    supports_tools: bool
    supports_structured_output: bool
    supports_vision: bool
    supports_prompt_cache: bool
    pricing: dict[str, str]
    availability_state: str
    entitlement_state: str
    freshness_state: str
    source_id: str
    source_version: str


class SelectorAPI:
    """Python facade around deterministic provider routing."""

    def __init__(self, registry: CapabilityRegistry | None = None) -> None:
        self._registry = registry or VerifiedCapabilityRegistry()
        self._selector = VerifiedProviderSelector(self._registry)

    def list_models(self) -> list[ModelSummary]:
        return [
            ModelSummary(
                provider=model.provider,
                surface=model.surface,
                model_id=model.model_id,
                aliases=list(model.aliases),
                model_family=model.model_family,
                context_window=model.context_window,
                max_output_tokens=model.max_output_tokens,
                reasoning_efforts=list(model.reasoning_efforts),
                speed_class=model.speed_class,
                supports_prompt_cache=model.supports_prompt_cache,
                availability_state=model.availability_state,
                entitlement_state=model.entitlement_state,
                freshness_state=model.freshness_state,
            )
            for model in self._registry.list_available_models()
        ]

    def get_model(self, model_id: str) -> CapabilityDetail | None:
        capability = self._registry.get(model_id)
        if capability is None:
            return None
        return CapabilityDetail(
            provider=capability.provider,
            surface=capability.surface,
            model_id=capability.model_id,
            aliases=list(capability.aliases),
            model_family=capability.model_family,
            context_window=capability.context_window,
            max_output_tokens=capability.max_output_tokens,
            reasoning_modes=list(capability.reasoning_modes),
            reasoning_efforts=list(capability.reasoning_efforts),
            speed_class=capability.speed_class,
            supports_tools=capability.supports_tools,
            supports_structured_output=capability.supports_structured_output,
            supports_vision=capability.supports_vision,
            supports_prompt_cache=capability.supports_prompt_cache,
            pricing={
                "input_per_1k": str(
                    capability.pricing.input_price_per_1k_tokens
                ),
                "cached_input_per_1k": str(
                    capability.pricing.cached_input_price_per_1k_tokens
                ),
                "output_per_1k": str(
                    capability.pricing.output_price_per_1k_tokens
                ),
                "unit": capability.pricing.price_unit,
            },
            availability_state=capability.availability_state,
            entitlement_state=capability.entitlement_state,
            freshness_state=capability.freshness_state,
            source_id=capability.source_id,
            source_version=capability.source_version,
        )

    def select(self, request: SelectRequest) -> SelectResponse:
        try:
            selection = ProviderSelection.model_validate(request.model_dump())
            planned = self._selector.select(selection)
            route = ResolvedRoute(
                provider=planned.provider,
                resolved_surface=planned.resolved_surface,
                model_id=planned.model_id,
                reasoning_mode=planned.reasoning_mode,
                reasoning_effort=planned.reasoning_effort,
                profile=planned.profile,
                capability_snapshot_hash=planned.capability_snapshot_hash,
                fallback_used=planned.fallback_used,
                fallback_reason=planned.fallback_reason,
            )
            return SelectResponse(
                status="ok",
                route=route,
                available_models=self.list_models(),
            )
        except ValueError as exc:
            return SelectResponse(
                status="error",
                error=str(exc),
                available_models=self.list_models(),
            )
