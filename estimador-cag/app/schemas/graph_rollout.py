"""Safe public records for legacy-versus-graph shadow comparisons."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ShadowComparisonStatus = Literal["completed", "failed"]


class ShadowComparisonRecord(BaseModel):
    """Sanitized migration evidence without transcript or provider payloads."""

    model_config = ConfigDict(extra="forbid")

    comparison_id: UUID
    created_at: datetime
    status: ShadowComparisonStatus
    request_fingerprint: str = Field(min_length=16, max_length=64)
    session_id: str | None = None
    served_backend: Literal["legacy"] = "legacy"
    shadow_backend: Literal["graph"] = "graph"
    primary_latency_ms: int = Field(ge=0)
    shadow_latency_ms: int = Field(ge=0)
    latency_delta_ms: int
    primary_total_cost_eur: float | None = Field(default=None, ge=0)
    shadow_total_cost_eur: float | None = Field(default=None, ge=0)
    cost_delta_eur: float | None = None
    primary_text_chars: int = Field(ge=0)
    shadow_text_chars: int = Field(ge=0)
    primary_structured_result: bool
    shadow_graph_status: str | None = None
    shadow_review_required: bool | None = None
    error_type: str | None = None
    error_message: str | None = None


class ShadowComparisonList(BaseModel):
    """Bounded newest-first shadow dashboard response."""

    model_config = ConfigDict(extra="forbid")

    count: int = Field(ge=0)
    comparisons: list[ShadowComparisonRecord]
