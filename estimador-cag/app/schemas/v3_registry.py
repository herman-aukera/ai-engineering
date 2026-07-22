"""Versioned model-registry contracts for Session 13 Plus V3.

Each record follows the lifecycle defined in
``docs/session13_plus_v3_foundation.md`` §4:

    documented → configured → reachable → contract_verified
    → benchmark_calibrated → enabled
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.v3_routing import StrictV3Model

CalibrationStatus = Literal[
    "documented",
    "configured",
    "reachable",
    "contract_verified",
    "benchmark_calibrated",
    "enabled",
]

Availability = Literal[
    "available",
    "unavailable",
    "degraded",
    "deprecated",
]

Modality = Literal[
    "text",
    "image",
    "audio",
    "video",
]

ReasoningEffort = Literal[
    "none",
    "low",
    "medium",
    "high",
    "max",
    "xhigh",
]


class ModelRecord(StrictV3Model):
    """One versioned, checkpoint-safe entry in the capability registry."""

    provider: str = Field(min_length=1, max_length=120)
    provider_model_id: str = Field(min_length=1, max_length=240)
    display_name: str = Field(min_length=1, max_length=240)
    capability_tier: str = Field(min_length=1, max_length=120)
    context_window: int = Field(gt=0, le=10_000_000)
    max_output: int = Field(gt=0, le=1_000_000)
    input_modalities: list[Modality] = Field(default_factory=list, max_length=10)
    tool_support: bool = False
    structured_output_support: bool = False
    reasoning_efforts: list[ReasoningEffort] = Field(default_factory=list, max_length=10)
    speed_class: str = Field(min_length=1, max_length=120)
    cost_metadata_version: str = Field(min_length=1, max_length=240)
    availability: Availability
    verified_at: datetime | None = None
    calibration_status: CalibrationStatus
