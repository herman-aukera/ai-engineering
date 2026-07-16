"""Typed Critic and deterministic Boss contracts for Session 13 Plus."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictReviewModel(BaseModel):
    """Reject undeclared fields at orchestration policy boundaries."""

    model_config = ConfigDict(extra="forbid")


class CriticIssueCode(StrEnum):
    """Machine-actionable review categories supported by the control room."""

    UNSUPPORTED_SCOPE = "unsupported_scope"
    MISSING_REQUIREMENT = "missing_requirement"
    RETRIEVAL_GAP = "retrieval_gap"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    UNRELIABLE_ESTIMATE = "unreliable_estimate"
    ARITHMETIC_MISMATCH = "arithmetic_mismatch"
    DANGLING_CITATION = "dangling_citation"
    POLICY_VIOLATION = "policy_violation"
    INCOMPLETE_TRACE = "incomplete_trace"
    PROVIDER_RUNTIME_ANOMALY = "provider_runtime_anomaly"
    NO_DATA = "no_data"


CriticSeverity = Literal["info", "minor", "major", "critical"]
CriticVerdict = Literal["accept", "needs_iteration", "reject", "human_required"]
RepairScope = Literal[
    "none",
    "selected_component",
    "selected_node",
    "full_graph",
    "human",
]


class CriticFinding(StrictReviewModel):
    """One evidence-linked finding that policy can route deterministically."""

    code: CriticIssueCode
    severity: CriticSeverity
    state_path: str = Field(min_length=1, max_length=240)
    explanation: str = Field(min_length=5, max_length=2000)
    evidence_refs: list[str] = Field(default_factory=list)
    proposed_repair: str | None = Field(default=None, max_length=2000)
    repair_scope: RepairScope = "none"
    component_ids: list[str] = Field(default_factory=list)
    node: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_repair_contract(self) -> "CriticFinding":
        if self.repair_scope == "none" and self.proposed_repair is not None:
            raise ValueError("repair_scope=none must not include proposed_repair")
        if self.repair_scope != "none" and not self.proposed_repair:
            raise ValueError("repairable findings must include proposed_repair")
        if self.repair_scope == "selected_component" and not self.component_ids:
            raise ValueError("selected_component repair requires component_ids")
        return self


class CriticReport(StrictReviewModel):
    """Structured review output consumed by deterministic policy."""

    verdict: CriticVerdict
    issues: list[CriticFinding] = Field(default_factory=list)
    confidence_in_review: float = Field(ge=0, le=1)
    summary: str = Field(min_length=5, max_length=2000)

    @model_validator(mode="after")
    def validate_verdict_contract(self) -> "CriticReport":
        serious_issues = [
            issue for issue in self.issues if issue.severity in {"major", "critical"}
        ]
        repairable_issues = [
            issue for issue in self.issues if issue.repair_scope != "none"
        ]

        if self.verdict == "accept" and serious_issues:
            raise ValueError("accept verdict cannot contain major or critical issues")
        if self.verdict == "needs_iteration" and not repairable_issues:
            raise ValueError("needs_iteration requires at least one repairable issue")
        if self.verdict in {"reject", "human_required"} and not self.issues:
            raise ValueError(f"{self.verdict} verdict requires at least one issue")
        return self


ProviderFailureKind = Literal[
    "none",
    "timeout",
    "rate_limit",
    "malformed_output",
    "unavailable",
]
BossAction = Literal[
    "accept",
    "retry_selected",
    "fallback_provider",
    "human_review",
    "reject",
]


class ExecutionBudgetSnapshot(StrictReviewModel):
    """Current bounded resources available to the orchestration policy."""

    retry_count: int = Field(default=0, ge=0)
    retry_limit: int = Field(default=2, ge=0)
    fallback_count: int = Field(default=0, ge=0)
    fallback_limit: int = Field(default=1, ge=0)
    tool_call_count: int = Field(default=0, ge=0)
    tool_call_limit: int = Field(default=8, ge=0)
    elapsed_ms: int = Field(default=0, ge=0)
    latency_budget_ms: int = Field(default=120_000, ge=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0)
    cost_budget_usd: float = Field(default=1.0, ge=0)

    @property
    def retry_available(self) -> bool:
        return self.retry_count < self.retry_limit

    @property
    def fallback_available(self) -> bool:
        return self.fallback_count < self.fallback_limit

    @property
    def tool_budget_available(self) -> bool:
        return self.tool_call_count < self.tool_call_limit

    @property
    def latency_available(self) -> bool:
        return self.elapsed_ms < self.latency_budget_ms

    @property
    def cost_available(self) -> bool:
        return self.estimated_cost_usd < self.cost_budget_usd


class BossDecision(StrictReviewModel):
    """One explicit, auditable orchestration-policy decision."""

    action: BossAction
    reason: str = Field(min_length=5, max_length=2000)
    issue_codes: list[CriticIssueCode] = Field(default_factory=list)
    selected_state_paths: list[str] = Field(default_factory=list)
    selected_component_ids: list[str] = Field(default_factory=list)
    next_provider: str | None = Field(default=None, max_length=120)
    remaining_retry_budget: int = Field(ge=0)
    remaining_fallback_budget: int = Field(ge=0)
    remaining_tool_call_budget: int = Field(ge=0)
