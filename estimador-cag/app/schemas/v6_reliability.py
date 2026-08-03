"""Reliability-analyst contracts for Session 13 Plus V6."""

from __future__ import annotations

from pydantic import Field

from app.schemas.v3_routing import StrictV3Model


class ComponentReliability(StrictV3Model):
    """Reliability score for one component estimate."""

    component_id: str = Field(min_length=1, max_length=120)
    reliability_score: float = Field(ge=0, le=1)
    reference_count: int = Field(default=0, ge=0)
    dispersion: float | None = None
    grounding_status: str = "unknown"
    flags: list[str] = Field(default_factory=list)


class ReliabilityReport(StrictV3Model):
    """Checkpoint-safe reliability analysis over component estimates."""

    components: list[ComponentReliability] = Field(default_factory=list)
    overall_score: float = Field(ge=0, le=1)
    requires_human_review: bool = False
    summary: str = Field(default="", min_length=0, max_length=2000)
