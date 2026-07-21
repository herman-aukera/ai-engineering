"""Checkpoint-safe contracts for Session 13 Plus adaptive model routing."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ComplexityLevel = Literal["C0", "C1", "C2", "C3", "C4", "C5"]
ExecutionProfileV3 = Literal["cost_first", "balanced", "quality_first", "human_controlled"]
ModelMode = Literal["deterministic", "instant", "thinking"]
ReasoningEffort = Literal["none", "low", "medium", "high", "max"]
RoutingStage = Literal["complexity", "structure", "recovery", "reliability", "proposal"]


class StrictV3Model(BaseModel):
    """Strict immutable base for checkpoint and audit records."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ComplexitySignals(StrictV3Model):
    """Deterministic project signals used before semantic classification."""

    requirement_count: int = Field(default=0, ge=0, le=500)
    integration_count: int = Field(default=0, ge=0, le=100)
    non_functional_requirement_count: int = Field(default=0, ge=0, le=100)
    ambiguous_requirement_count: int = Field(default=0, ge=0, le=100)
    missing_information_count: int = Field(default=0, ge=0, le=100)
    contradiction_count: int = Field(default=0, ge=0, le=100)
    attachment_count: int = Field(default=0, ge=0, le=100)
    detected_language_count: int = Field(default=1, ge=1, le=20)
    transcript_chars: int = Field(default=0, ge=0, le=1_000_000)
    compliance_or_security_critical: bool = False
    data_migration_required: bool = False
    workflow_state_complexity: bool = False
    evidence_scarcity: bool = False
    novel_domain: bool = False


class ComplexityAssessment(StrictV3Model):
    """Versioned deterministic baseline for project and routing complexity."""

    level: ComplexityLevel
    score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    dimensions: dict[str, int]
    reasons: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    detected_languages: list[str] = Field(default_factory=list)
    classifier_version: str = Field(min_length=1)
    human_review_required: bool = False

    @model_validator(mode="after")
    def validate_dimension_total(self) -> "ComplexityAssessment":
        if any(value < 0 for value in self.dimensions.values()):
            raise ValueError("complexity dimensions must be non-negative")
        if sum(self.dimensions.values()) != self.score:
            raise ValueError("complexity dimensions must sum to score")
        if self.level == "C5" and not self.human_review_required:
            raise ValueError("C5 complexity requires human review")
        return self


class ModelRoute(StrictV3Model):
    """One planned model route for a graph stage."""

    route_id: str = Field(min_length=1)
    stage: RoutingStage
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    mode: ModelMode
    effort: ReasoningEffort = "none"
    max_output_tokens: int = Field(ge=0)
    timeout_ms: int = Field(gt=0)
    tool_call_limit: int = Field(ge=0)
    cost_limit_usd: float = Field(ge=0)
    fallback_route_ids: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class ModelRoutingPlan(StrictV3Model):
    """Immutable project routing plan produced before graph model execution."""

    plan_id: str = Field(min_length=1)
    project_complexity: ComplexityAssessment
    profile: ExecutionProfileV3
    routes_by_stage: dict[RoutingStage, ModelRoute]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
