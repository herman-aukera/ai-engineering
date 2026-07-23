"""Tests for Session 13 Plus S5: provider selector contracts and service."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# 1. ProviderSelection schema
# ---------------------------------------------------------------------------

def test_provider_selection_defaults_to_deepseek_medium() -> None:
    """Default provider must be DeepSeek with medium reasoning and context."""
    from app.schemas.v5_provider_selection import ProviderSelection

    sel = ProviderSelection()
    assert sel.provider == "deepseek"
    assert sel.reasoning == "medium"
    assert sel.context_detail == "medium"


def test_provider_selection_validates_provider_values() -> None:
    """provider must be one of auto, deepseek, kimi, openai."""
    from app.schemas.v5_provider_selection import ProviderSelection

    for valid in ("auto", "deepseek", "kimi", "openai"):
        sel = ProviderSelection(provider=valid)
        assert sel.provider == valid

    with pytest.raises(ValidationError):
        ProviderSelection(provider="anthropic")


def test_provider_selection_validates_reasoning_values() -> None:
    """reasoning must be minimal, medium, or max."""
    from app.schemas.v5_provider_selection import ProviderSelection

    for valid in ("minimal", "medium", "max"):
        sel = ProviderSelection(reasoning=valid)
        assert sel.reasoning == valid

    with pytest.raises(ValidationError):
        ProviderSelection(reasoning="ultra")


def test_provider_selection_validates_context_detail_values() -> None:
    """context_detail must be minimal, medium, or max."""
    from app.schemas.v5_provider_selection import ProviderSelection

    for valid in ("minimal", "medium", "max"):
        sel = ProviderSelection(context_detail=valid)
        assert sel.context_detail == valid

    with pytest.raises(ValidationError):
        ProviderSelection(context_detail="extreme")


def test_provider_selection_is_checkpoint_safe() -> None:
    """ProviderSelection must round-trip through model_dump(mode='json')."""
    from app.schemas.v5_provider_selection import ProviderSelection

    sel = ProviderSelection(provider="kimi", reasoning="max", context_detail="max")
    payload = sel.model_dump(mode="json")
    assert payload["provider"] == "kimi"
    assert payload["reasoning"] == "max"
    assert payload["context_detail"] == "max"


# ---------------------------------------------------------------------------
# 2. Provider route resolution
# ---------------------------------------------------------------------------

def test_auto_selects_deepseek_flash_for_low_complexity() -> None:
    """Auto must select DeepSeek Flash for C0/C1/C2 complexity (least expensive)."""
    from app.schemas.v5_provider_selection import ProviderSelection
    from app.services.v5_provider_selector import resolve_provider_route

    sel = ProviderSelection(provider="auto")
    route = resolve_provider_route(selection=sel, complexity_level="C1", stage="structure")

    assert route["provider"] == "deepseek"
    assert route["model"] == "deepseek-v4-flash"


def test_auto_selects_deepseek_pro_for_high_complexity() -> None:
    """Auto must select DeepSeek Pro for C4/C5 complexity."""
    from app.schemas.v5_provider_selection import ProviderSelection
    from app.services.v5_provider_selector import resolve_provider_route

    sel = ProviderSelection(provider="auto")
    route = resolve_provider_route(selection=sel, complexity_level="C5", stage="structure")

    assert route["provider"] == "deepseek"
    assert route["model"] == "deepseek-v4-pro"


def test_explicit_deepseek_uses_deepseek_models() -> None:
    """Explicit DeepSeek selection must always use DeepSeek models."""
    from app.schemas.v5_provider_selection import ProviderSelection
    from app.services.v5_provider_selector import resolve_provider_route

    sel = ProviderSelection(provider="deepseek")
    route = resolve_provider_route(selection=sel, complexity_level="C3", stage="complexity")

    assert route["provider"] == "deepseek"


def test_explicit_kimi_uses_kimi_models() -> None:
    """Explicit Kimi selection must use Kimi models."""
    from app.schemas.v5_provider_selection import ProviderSelection
    from app.services.v5_provider_selector import resolve_provider_route

    sel = ProviderSelection(provider="kimi")
    route = resolve_provider_route(selection=sel, complexity_level="C3", stage="structure")

    assert route["provider"] == "moonshot"


def test_explicit_openai_uses_openai_models() -> None:
    """Explicit OpenAI selection must use OpenAI models."""
    from app.schemas.v5_provider_selection import ProviderSelection
    from app.services.v5_provider_selector import resolve_provider_route

    sel = ProviderSelection(provider="openai")
    route = resolve_provider_route(selection=sel, complexity_level="C4", stage="structure")

    assert route["provider"] == "openai"


def test_reasoning_intent_maps_to_effort() -> None:
    """minimal/medium/max reasoning must map to none/high/max effort."""
    from app.schemas.v5_provider_selection import ProviderSelection
    from app.services.v5_provider_selector import resolve_provider_route

    minimal = resolve_provider_route(
        selection=ProviderSelection(provider="deepseek", reasoning="minimal"),
        complexity_level="C3", stage="structure",
    )
    assert minimal["effort"] == "none"

    medium = resolve_provider_route(
        selection=ProviderSelection(provider="deepseek", reasoning="medium"),
        complexity_level="C3", stage="structure",
    )
    assert medium["effort"] == "high"

    max_route = resolve_provider_route(
        selection=ProviderSelection(provider="deepseek", reasoning="max"),
        complexity_level="C3", stage="structure",
    )
    assert max_route["effort"] == "max"


def test_resolve_route_for_unknown_stage_raises() -> None:
    """An unrecognised stage must raise ValueError."""
    from app.schemas.v5_provider_selection import ProviderSelection
    from app.services.v5_provider_selector import resolve_provider_route

    sel = ProviderSelection()
    with pytest.raises(ValueError, match="stage"):
        resolve_provider_route(selection=sel, complexity_level="C1", stage="unknown_stage")


def test_resolve_route_is_deterministic() -> None:
    """Same inputs must produce identical routes."""
    from app.schemas.v5_provider_selection import ProviderSelection
    from app.services.v5_provider_selector import resolve_provider_route

    sel = ProviderSelection(provider="auto", reasoning="medium")
    a = resolve_provider_route(selection=sel, complexity_level="C3", stage="reliability")
    b = resolve_provider_route(selection=sel, complexity_level="C3", stage="reliability")
    assert a == b
