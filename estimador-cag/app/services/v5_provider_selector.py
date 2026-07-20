"""Provider-route resolution service for Session 13 Plus V5.

Maps the user-facing :class:`ProviderSelection` to a concrete provider,
model, and reasoning effort for a given complexity level and graph stage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas.v3_routing import ComplexityLevel, ReasoningEffort
from app.schemas.v5_provider_selection import (
    ProviderOption,
    ProviderSelection,
    ReasoningIntent,
)

if TYPE_CHECKING:
    from app.services.v3_model_registry import ModelRegistry

_VALID_STAGES: set[str] = {
    "complexity",
    "structure",
    "recovery",
    "reliability",
    "proposal",
}

_EFFORT_MAP: dict[ReasoningIntent, ReasoningEffort] = {
    "minimal": "none",
    "medium": "high",
    "max": "max",
}

# Hardcoded defaults used when no registry is available (backward compatible).
_DEFAULTS: dict[ProviderOption, dict[str, list[dict[str, str]]]] = {
    "auto": {
        "deepseek": [
            {"model": "deepseek-v4-flash", "tier": "flash"},
            {"model": "deepseek-v4-pro", "tier": "pro"},
        ],
    },
    "deepseek": {
        "deepseek": [
            {"model": "deepseek-v4-flash", "tier": "flash"},
            {"model": "deepseek-v4-pro", "tier": "pro"},
        ],
    },
    "kimi": {
        "moonshot": [
            {"model": "kimi-k2.6", "tier": "flash"},
            {"model": "kimi-k2.7-code", "tier": "pro"},
            {"model": "kimi-k3", "tier": "max"},
        ],
    },
    "openai": {
        "openai": [
            {"model": "gpt-5.6-luna", "tier": "flash"},
            {"model": "gpt-5.6-terra", "tier": "pro"},
            {"model": "gpt-5.6-sol", "tier": "max"},
        ],
    },
}

_TIER_FOR_COMPLEXITY: dict[ComplexityLevel, str] = {
    "C0": "flash",
    "C1": "flash",
    "C2": "flash",
    "C3": "pro",
    "C4": "pro",
    "C5": "max",
}


def _select_from_candidates(
    candidates: list[dict[str, str]],
    preferred_tier: str,
) -> dict[str, str] | None:
    """Select the best candidate: preferred tier first, then fall back through tiers."""
    tiers = [preferred_tier, "pro", "flash"]  # Preferred → fallback order
    for tier in tiers:
        for candidate in candidates:
            if candidate.get("tier") == tier:
                return candidate
    return None


def resolve_provider_route(
    *,
    selection: ProviderSelection,
    complexity_level: ComplexityLevel,
    stage: str,
    registry: ModelRegistry | None = None,
) -> dict[str, str]:
    """Resolve a concrete provider, model, and effort for one graph stage.

    When *registry* is provided, models are looked up from enabled + available
    registry entries.  When *registry* is ``None``, hardcoded defaults are used
    (backward compatible).

    Returns a dict with keys ``provider``, ``model``, and ``effort``.
    Raises :exc:`ValueError` if no eligible route exists.
    """
    if stage not in _VALID_STAGES:
        raise ValueError(
            f"Unknown stage: {stage!r}.  Valid stages: {', '.join(sorted(_VALID_STAGES))}"
        )

    effort = _EFFORT_MAP[selection.reasoning]
    preferred_tier = _TIER_FOR_COMPLEXITY[complexity_level]

    if registry is not None and selection.provider != "auto":
        # Registry-backed: find enabled + available models for this provider.
        candidates = [
            {
                "provider": record.provider,
                "model": record.provider_model_id,
                "tier": record.capability_tier,
            }
            for record in registry.list_by_provider(_provider_name(selection.provider))
            if record.calibration_status == "enabled"
            and record.availability == "available"
        ]
        if not candidates:
            raise ValueError(
                f"No eligible models for provider={selection.provider} "
                f"(enabled + available required)"
            )
        chosen = _select_from_candidates(candidates, preferred_tier)
        if chosen is None:
            raise ValueError(
                f"No eligible route for provider={selection.provider}, "
                f"complexity={complexity_level}"
            )
        chosen["effort"] = effort
        return chosen

    if registry is not None and selection.provider == "auto":
        # Auto: find the least expensive enabled model across all providers.
        all_candidates = [
            {
                "provider": record.provider,
                "model": record.provider_model_id,
                "tier": record.capability_tier,
            }
            for record in registry.list_enabled()
            if record.availability == "available"
        ]
        if not all_candidates:
            raise ValueError("No eligible models for auto (enabled + available required)")
        chosen = _select_from_candidates(all_candidates, preferred_tier)
        if chosen is None:
            raise ValueError(
                f"No eligible auto route for complexity={complexity_level}"
            )
        chosen["effort"] = effort
        return chosen

    # No registry — use hardcoded defaults (backward compatible).
    defaults = _DEFAULTS[selection.provider]
    provider_name = next(iter(defaults))
    candidates = [
        {"provider": provider_name, "model": c["model"], "tier": c["tier"]}
        for c in defaults[provider_name]
    ]
    chosen = _select_from_candidates(candidates, preferred_tier)
    if chosen is None:
        raise ValueError(
            f"No default route for provider={selection.provider}, "
            f"complexity={complexity_level}"
        )
    chosen["effort"] = effort
    return chosen


def _provider_name(option: ProviderOption) -> str:
    """Map the user-facing provider option to the registry provider name."""
    return {
        "deepseek": "deepseek",
        "kimi": "moonshot",
        "openai": "openai",
        "auto": "deepseek",
    }[option]
