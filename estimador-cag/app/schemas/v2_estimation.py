"""Canonical public contract for the unified estimation product."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.schemas.human_review import HumanReviewMode

ExecutionProfile = Literal["cost_first", "balanced", "quality_first", "human_controlled"]
EstimationStage = Literal[
    "context",
    "reformulation",
    "structure",
    "evidence",
    "estimation",
    "critic_boss",
    "human_approval",
    "audit",
    "completed",
]


class StrictV2Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectContextV2(StrictV2Model):
    transcript: str = Field(min_length=20, max_length=50_000)
    project_type: str | None = Field(default=None, max_length=120)
    constraints: list[str] = Field(default_factory=list, max_length=100)
    acceptance_criteria: list[str] = Field(default_factory=list, max_length=100)


class RequirementV2(StrictV2Model):
    requirement_id: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=2_000)


class SourceProvenanceV2(StrictV2Model):
    evidence_id: str = Field(min_length=1, max_length=240)
    budget_id: str | None = Field(default=None, max_length=240)
    source_document_id: str | None = Field(default=None, max_length=240)
    source_chunk_id: str | None = Field(default=None, max_length=240)
    retrieval_method: str | None = Field(default=None, max_length=120)
    score: float | None = None


class BudgetEvidenceV2(StrictV2Model):
    evidence_id: str = Field(min_length=1, max_length=240)
    recorded_hours: float | None = Field(default=None, ge=0)
    provenance: SourceProvenanceV2


class TaskEstimateV2(StrictV2Model):
    hours_low: float | None = Field(default=None, ge=0)
    hours_expected: float | None = Field(default=None, ge=0)
    hours_high: float | None = Field(default=None, ge=0)
    hourly_rate_eur: float = Field(default=0, ge=0)
    confidence: float = Field(default=0, ge=0, le=1)
    derivation_method: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_hour_range(self) -> TaskEstimateV2:
        values = (self.hours_low, self.hours_expected, self.hours_high)
        if all(value is not None for value in values):
            low, expected, high = values
            if not low <= expected <= high:  # type: ignore[operator]
                raise ValueError("hours_low must be <= hours_expected <= hours_high")
        return self

    @computed_field
    @property
    def cost_eur(self) -> float | None:
        if self.hours_expected is None:
            return None
        return round(self.hours_expected * self.hourly_rate_eur, 2)


class TaskV2(StrictV2Model):
    task_id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=2_000)
    category: str = Field(min_length=1, max_length=120)
    requirement_ids: list[str] = Field(default_factory=list)
    estimate: TaskEstimateV2 | None = None
    evidence: list[BudgetEvidenceV2] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    active_finding_codes: list[str] = Field(default_factory=list)
    review_status: str = "pending"


class WorkModuleV2(StrictV2Model):
    module_id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=2_000)
    tasks: list[TaskV2] = Field(default_factory=list)

    @computed_field
    @property
    def total_hours(self) -> float:
        return round(
            sum(task.estimate.hours_expected or 0 for task in self.tasks if task.estimate),
            2,
        )

    @computed_field
    @property
    def total_cost_eur(self) -> float:
        return round(
            sum(task.estimate.cost_eur or 0 for task in self.tasks if task.estimate),
            2,
        )


class ExecutionPolicyV2(StrictV2Model):
    profile: ExecutionProfile
    primary_provider: str
    fallback_provider: str | None = None
    retry_limit: int = Field(ge=0)
    timeout_seconds: float = Field(gt=0)
    max_concurrency: int = Field(ge=1)
    tool_call_limit: int = Field(ge=0)
    cost_limit_usd: float = Field(ge=0)
    confidence_threshold: float = Field(ge=0, le=1)
    human_review_mode: HumanReviewMode


class ProviderUsageV2(StrictV2Model):
    provider: str
    model: str | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    latency_ms: int | None = Field(default=None, ge=0)


class HumanDecisionV2(StrictV2Model):
    gate: Literal["structure", "final"]
    action: str
    revision: int = Field(ge=0)
    actor: str | None = None
    reason: str | None = None
    changes: list[dict[str, Any]] = Field(default_factory=list)


class ScenarioLineageV2(StrictV2Model):
    scenario_id: str | None = None
    parent_estimation_id: UUID | None = None
    parent_checkpoint_id: str | None = None


class AuditMetadataV2(StrictV2Model):
    graph_version: str
    checkpoint_count: int = Field(default=0, ge=0)
    trace_url: str | None = None


class EstimationV2(StrictV2Model):
    schema_version: Literal["estimation.v2"] = "estimation.v2"
    estimation_id: UUID
    thread_id: str
    execution_status: Literal["paused", "completed"]
    stage: EstimationStage
    graph_status: Literal["pending", "validated", "needs_review"]
    revision: int = Field(ge=0)
    requirements: list[RequirementV2]
    modules: list[WorkModuleV2]
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    critic_report: dict[str, Any] = Field(default_factory=dict)
    boss_decision: dict[str, Any] = Field(default_factory=dict)
    human_decisions: list[HumanDecisionV2] = Field(default_factory=list)
    execution_policy: ExecutionPolicyV2
    provider_usage: list[ProviderUsageV2] = Field(default_factory=list)
    lineage: ScenarioLineageV2 = Field(default_factory=ScenarioLineageV2)
    audit: AuditMetadataV2

    @computed_field
    @property
    def total_hours(self) -> float:
        return round(sum(module.total_hours for module in self.modules), 2)

    @computed_field
    @property
    def total_cost_eur(self) -> float:
        return round(sum(module.total_cost_eur for module in self.modules), 2)


class EstimationV2CreateRequest(StrictV2Model):
    context: ProjectContextV2
    profile: ExecutionProfile = "balanced"
    estimation_id: UUID | None = None


class EstimationV2ActionRequest(StrictV2Model):
    gate: Literal["structure", "final"]
    action: Literal[
        "approve", "edit", "reject", "regenerate", "request_recovery", "override"
    ]
    expected_revision: int = Field(ge=0)
    actor: str | None = Field(default=None, max_length=240)
    reason: str | None = Field(default=None, max_length=2_000)
    requirements: list[RequirementV2] | None = None
    modules: list[WorkModuleV2] | None = None
    overrides: list[dict[str, Any]] | None = None

    @model_validator(mode="after")
    def validate_gate_contract(self) -> EstimationV2ActionRequest:
        structure_actions = {"approve", "edit", "reject", "regenerate"}
        final_actions = {"approve", "reject", "request_recovery", "override"}
        allowed = structure_actions if self.gate == "structure" else final_actions
        if self.action not in allowed:
            raise ValueError(f"{self.action} is not valid for the {self.gate} gate")
        if self.gate == "final" and not (self.actor or "").strip():
            raise ValueError("final gate actions require actor")
        if self.action == "edit" and (not self.requirements or not self.modules):
            raise ValueError("structure edit requires requirements and modules")
        return self


class EstimationV2Response(StrictV2Model):
    estimation: EstimationV2
    next_actions: list[str]
    interrupts: list[dict[str, Any]] = Field(default_factory=list)


class CheckpointSummaryV2(StrictV2Model):
    checkpoint_id: str
    created_at: str | None = None
    next_nodes: list[str]
    stage: EstimationStage


class EstimationV2CheckpointHistory(StrictV2Model):
    estimation_id: UUID
    checkpoints: list[CheckpointSummaryV2]
