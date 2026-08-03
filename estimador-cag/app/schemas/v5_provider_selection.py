"""Provider-selector contracts for Session 13 Plus V5."""

from __future__ import annotations

from typing import Literal

from app.schemas.v3_routing import StrictV3Model

ProviderOption = Literal["auto", "deepseek", "kimi", "openai"]
ReasoningIntent = Literal["minimal", "medium", "max"]
ContextDetail = Literal["minimal", "medium", "max"]


class ProviderSelection(StrictV3Model):
    """User-facing provider, reasoning, and context-detail selection.

    Defaults match the canonical policy: DeepSeek, medium reasoning,
    medium context detail.
    """

    provider: ProviderOption = "deepseek"
    reasoning: ReasoningIntent = "medium"
    context_detail: ContextDetail = "medium"
