"""Typed contracts for the deterministic Energy Aware Chat evaluator."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Decision = Literal["accept", "repair", "reject", "clarify"]
ConstraintType = Literal["hard_reject", "hard_repair", "soft"]
Mode = Literal["chat_lite", "research", "project", "tutor"]


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
