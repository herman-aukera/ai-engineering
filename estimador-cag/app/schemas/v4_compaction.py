"""Context-compaction contracts for Session 13 Plus V4."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.v3_routing import StrictV3Model

CompactionLevel = Literal["minimal", "medium", "max"]


class CompactionMetadata(StrictV3Model):
    """Checkpoint-safe record of one compaction operation."""

    original_token_estimate: int = Field(ge=0)
    compacted_token_estimate: int = Field(ge=0)
    compaction_level: CompactionLevel
    compaction_version: str = Field(min_length=1, max_length=240)
