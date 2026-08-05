"""Typed contracts for the deterministic Energy Aware Chat evaluator."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Decision = Literal["accept", "repair", "reject", "clarify", "refuse", "escalate"]
PolicyDirective = Literal["continue", "refuse", "escalate"]
ConstraintType = Literal["hard_reject", "hard_repair", "soft"]
Mode = Literal["chat_lite", "research", "project", "tutor"]
DeepSeekTier = Literal["flash", "pro"]
ProviderTier = Literal["flash", "pro", "backup", "backup_pro"]
SourceNeedDecision = Literal[
    "sources_not_required",
    "sources_recommended",
    "sources_required",
]
EvidenceKind = Literal[
    "git",
    "test",
    "ci",
    "file",
    "source",
    "web",
    "manual",
    "cmd",
    "unknown",
]


class EnergyChatRequest(BaseModel):
    """Input evaluated by the deterministic chat critic pipeline."""

    user_message: str
    draft_answer: str
    mode: Mode = "chat_lite"
    required_constraints: list[str] = Field(default_factory=list)
    required_sections: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EnergyPolicy(BaseModel):
    """Energy thresholds and penalties for a chat evaluation run."""

    policy_id: str = "energy-chat-lite-default"
    version: str = "1.0.0"
    accept_max_energy: int = 120
    repair_min_energy: int = 121
    reject_on_any_hard_reject: bool = True
    max_repairs_mvp: int = 1
    penalties: dict[str, int] = Field(
        default_factory=lambda: {
            "hidden_chain_of_thought_requested": 1000,
            "fabricated_citation": 1000,
            "unsafe_answer": 1000,
            "executor_self_approved": 900,
            "leaked_or_private_source_recommended": 1000,
            "unsupported_current_claim": 900,
            "missing_project_evidence": 800,
            "missing_user_constraint": 800,
            "scope_explosion": 700,
            "missing_mode_requirement": 600,
            "missing_comparison": 500,
            "missing_tradeoffs": 400,
            "missing_next_action": 300,
            "insufficient_user_intent": 300,
            "too_generic": 120,
            "weak_structure": 80,
            "too_verbose": 80,
            "missing_example": 60,
        }
    )


class RequestPolicyAssessment(BaseModel):
    """Versioned deterministic request-level authority and refusal assessment."""

    version: str
    directive: PolicyDirective
    rule_id: str
    reason: str


class CriticFinding(BaseModel):
    """Structured violation or warning emitted by a deterministic critic."""

    critic: str
    violation_id: str
    constraint_type: ConstraintType
    penalty: int
    evidence: str
    repair_hint: str
    confidence: float = 1.0


class EnergyScore(BaseModel):
    """Aggregated energy score and categorized findings."""

    total_energy: int
    hard_reject_violations: list[str] = Field(default_factory=list)
    hard_repair_violations: list[str] = Field(default_factory=list)
    soft_violations: list[str] = Field(default_factory=list)
    findings: list[CriticFinding] = Field(default_factory=list)


class EnergyDecision(BaseModel):
    """Final evaluator decision for a candidate answer."""

    decision: Decision
    energy: int
    reasoning_summary: str
    policy_rule_id: str = "legacy_energy_decider"
    required_repairs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class EnergyCard(BaseModel):
    """User-visible summary of the energy-aware decision."""

    decision: Decision
    energy: int
    hard_constraints_passed: bool
    repairs: int
    evidence: list[str] = Field(default_factory=list)
    remaining_caveats: list[str] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    """Full deterministic evaluation result."""

    request: EnergyChatRequest
    policy: EnergyPolicy
    score: EnergyScore
    decision: EnergyDecision
    energy_card: EnergyCard


class RepairEvaluationResult(BaseModel):
    """One pass deterministic repair attempt result."""

    initial_result: EvaluationResult
    final_result: EvaluationResult
    repair_attempted: bool
    repairs_applied: list[str] = Field(default_factory=list)
    repaired_request: EnergyChatRequest | None = None
    repaired_result: EvaluationResult | None = None


class DeepSeekBaselineRequest(BaseModel):
    """Input for generating one plain DeepSeek draft before energy evaluation."""

    user_message: str
    mode: Mode = "chat_lite"
    tier: DeepSeekTier = "flash"
    max_tokens: int = Field(default=700, ge=64, le=4000)
    required_constraints: list[str] = Field(default_factory=list)
    required_sections: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeepSeekBaselineResult(BaseModel):
    """Provider-normalized plain draft result for benchmark capture."""

    request: DeepSeekBaselineRequest
    draft_answer: str
    provider: str
    model: str
    tier: ProviderTier
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    finish_reason: str | None = None
    fallback_used: bool = False
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeepSeekBenchmarkCase(BaseModel):
    """One fixed benchmark case used for measurement-only runs."""

    case_id: str
    user_message: str
    mode: Mode = "chat_lite"
    required_constraints: list[str] = Field(default_factory=list)
    required_sections: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeepSeekBenchmarkRequest(BaseModel):
    """Batch request for DeepSeek baseline plus Energy Aware measurement."""

    cases: list[DeepSeekBenchmarkCase] = Field(min_length=1, max_length=20)
    tier: DeepSeekTier = "flash"
    max_tokens: int = Field(default=700, ge=64, le=4000)
    run_id: str | None = None


class DeepSeekBenchmarkCaseResult(BaseModel):
    """Per-case benchmark measurement record."""

    case: DeepSeekBenchmarkCase
    baseline: DeepSeekBaselineResult
    baseline_evaluation: EvaluationResult
    repair_evaluation: RepairEvaluationResult
    final_decision: Decision
    final_energy: int
    energy_delta_after_repair: int
    accepted_after_repair: bool


class DeepSeekBenchmarkRunResult(BaseModel):
    """Measurement-only benchmark batch result."""

    run_id: str
    provider: str
    model: str
    tier: DeepSeekTier
    cases_total: int
    accepted_baseline: int
    accepted_after_repair: int
    repairs_attempted: int
    hard_rejects: int
    results: list[DeepSeekBenchmarkCaseResult] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceNeedRequest(BaseModel):
    """Input for deterministic source requirement classification."""

    user_message: str
    draft_answer: str | None = None
    mode: Mode = "chat_lite"
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceNeedResult(BaseModel):
    """Deterministic source requirement classification result."""

    decision: SourceNeedDecision
    requires_current_sources: bool
    requires_project_sources: bool
    missing_evidence: bool
    detected_markers: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    reasoning_summary: str
    next_action: str


class EvidenceItem(BaseModel):
    """One normalized evidence reference visible to the evaluator or demo."""

    ref: str
    source_type: EvidenceKind
    trusted: bool
    summary: str = ""


class EvidenceBundleRequest(BaseModel):
    """Input for building a deterministic evidence bundle."""

    mode: Mode = "project"
    evidence_refs: list[str] = Field(default_factory=list)
    command_outputs: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceBundleResult(BaseModel):
    """Normalized evidence refs plus project/research support checks."""

    mode: Mode
    evidence_refs: list[str] = Field(default_factory=list)
    trusted_refs: list[str] = Field(default_factory=list)
    missing_required_kinds: list[str] = Field(default_factory=list)
    items: list[EvidenceItem] = Field(default_factory=list)
    can_support_project_claim: bool
    can_support_current_claim: bool
    reasoning_summary: str
    next_action: str


class ProjectRagChunk(BaseModel):
    """One retrieved project-source chunk used as answer evidence."""

    source_id: str
    title: str
    content: str
    evidence_ref: str
    score: float = Field(ge=0.0)


class ProjectRagRequest(BaseModel):
    """Input for deterministic local RAG over committed project sources."""

    query: str
    mode: Mode = "project"
    k: int = Field(default=3, ge=1, le=8)


class ProjectRagResult(BaseModel):
    """Retrieved evidence chunks for project-grounded Energy Aware Chat answers."""

    query: str
    k: int
    retrieval_strategy: str
    results: list[ProjectRagChunk] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    grounding_summary: str


class EnergyAwareChatAgentRequest(BaseModel):
    """End-to-end local MVP chat request with retrieval, draft, critics, and Energy Card."""

    user_message: str
    mode: Mode = "project"
    k: int = Field(default=3, ge=1, le=8)
    required_constraints: list[str] = Field(default_factory=list)
    required_sections: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EnergyAwareChatAgentResult(BaseModel):
    """End-to-end local MVP chat result with visible evidence and decision trace."""

    request: EnergyAwareChatAgentRequest
    rag: ProjectRagResult
    draft_answer: str
    evaluation: EvaluationResult
    repair_evaluation: RepairEvaluationResult
    final_answer: str
    energy_card: EnergyCard
    agent_trace: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
