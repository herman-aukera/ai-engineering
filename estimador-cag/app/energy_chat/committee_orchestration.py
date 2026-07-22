"""Bounded deterministic committee generation and adaptive orchestration policy."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.energy_chat.candidate_provider import (
    CandidateGenerationResult,
    CandidateProviderRequest,
    DeterministicCandidateProvider,
)
from app.energy_chat.contracts import EnergyChatRequest, Mode
from app.energy_chat.evaluator import run_evaluation
from app.energy_chat.graph_state import GraphStateRecord, ProviderMetrics

CommitteeRole = Literal["grounded", "constraint_first", "skeptical"]
ResolvedOrchestrationMode = Literal["critic", "committee"]

_ROLE_ORDER: dict[CommitteeRole, int] = {
    "grounded": 0,
    "constraint_first": 1,
    "skeptical": 2,
}
_DECISION_ORDER = {
    "accept": 0,
    "repair": 1,
    "clarify": 2,
    "escalate": 3,
    "reject": 4,
    "refuse": 5,
}
_HIGH_RISK_MARKERS = (
    "latest",
    "current",
    "production",
    "release",
    "approve",
    "security",
    "medical",
    "legal",
    "financial",
    "investment",
)


class CommitteeProposal(GraphStateRecord):
    """One visible proposal and its independent deterministic evaluation."""

    proposal_id: str = Field(min_length=1)
    role: CommitteeRole
    answer: str = Field(min_length=1)
    total_energy: int = Field(ge=0)
    decision: str = Field(min_length=1)
    hard_reject_count: int = Field(ge=0)
    violation_count: int = Field(ge=0)


class CommitteeSelection(GraphStateRecord):
    """All bounded proposals and the stable Boss selection."""

    committee_id: str = Field(min_length=1)
    proposals: list[CommitteeProposal] = Field(min_length=3, max_length=3)
    selected_proposal_id: str = Field(min_length=1)
    selected_role: CommitteeRole
    selection_reason: str = Field(min_length=1)


class AdaptiveRouteDecision(GraphStateRecord):
    """Deterministic decision to stay on critic or escalate to committee."""

    resolved_mode: ResolvedOrchestrationMode
    reason_codes: list[str] = Field(default_factory=list)


class CommitteeCandidateProvider:
    """Three-proposal local committee with deterministic minimum-energy selection."""

    def __init__(self) -> None:
        self.last_selection: CommitteeSelection | None = None

    def generate(self, request: CandidateProviderRequest) -> CandidateGenerationResult:
        selection = build_committee_selection(request)
        self.last_selection = selection
        selected = next(
            item
            for item in selection.proposals
            if item.proposal_id == selection.selected_proposal_id
        )
        return CandidateGenerationResult(
            answer=selected.answer,
            evidence_refs=request.evidence_refs,
            metrics=ProviderMetrics(
                provider_call_id=request.provider_call_id,
                provider="deterministic_committee",
                model=f"energy-chat-committee-v1:{selected.role}",
                tier="local",
                input_tokens=_approx_tokens(request.user_request),
                output_tokens=_approx_tokens(selected.answer),
                cost_usd=0.0,
                latency_ms=0,
                retries=0,
                fallback_used=False,
                finish_reason=(
                    f"committee_selected:{selected.role};proposals:{len(selection.proposals)}"
                ),
            ),
        )


def build_committee_selection(request: CandidateProviderRequest) -> CommitteeSelection:
    """Generate three distinct local proposals and select the lowest-energy result."""

    baseline = DeterministicCandidateProvider().generate(request).answer
    variants: list[tuple[CommitteeRole, str]] = [
        ("grounded", baseline),
        (
            "constraint_first",
            _constraint_first_answer(
                baseline,
                constraints=request.constraints,
                required_sections=request.required_sections,
            ),
        ),
        ("skeptical", _skeptical_answer(baseline)),
    ]
    proposals: list[CommitteeProposal] = []
    for role, answer in variants:
        evaluation = run_evaluation(
            EnergyChatRequest(
                user_message=request.user_request,
                draft_answer=answer,
                mode=request.mode,
                required_constraints=request.constraints,
                required_sections=request.required_sections,
                evidence_refs=request.evidence_refs,
                metadata={
                    "orchestration_mode": "committee",
                    "committee_role": role,
                },
            )
        )
        score = evaluation.score
        proposals.append(
            CommitteeProposal(
                proposal_id=f"{request.provider_call_id}:proposal:{role}",
                role=role,
                answer=answer,
                total_energy=score.total_energy,
                decision=evaluation.decision.decision,
                hard_reject_count=len(score.hard_reject_violations),
                violation_count=len(score.findings),
            )
        )
    selected = min(proposals, key=_selection_key)
    return CommitteeSelection(
        committee_id=f"{request.provider_call_id}:committee",
        proposals=proposals,
        selected_proposal_id=selected.proposal_id,
        selected_role=selected.role,
        selection_reason=(
            "deterministic Boss selected minimum hard-reject count, then minimum "
            "constraint energy, then disposition and stable role order"
        ),
    )


def resolve_adaptive_orchestration(
    *,
    user_request: str,
    mode: Mode,
    constraints: list[str],
    required_sections: list[str],
) -> AdaptiveRouteDecision:
    """Escalate only when explicit risk/complexity signals justify committee cost."""

    normalized = user_request.casefold()
    reasons: list[str] = []
    if mode == "research":
        reasons.append("research_evidence_risk")
    if len(constraints) >= 2:
        reasons.append("multiple_hard_constraints")
    if len(required_sections) >= 3:
        reasons.append("multi_section_complexity")
    if len(user_request) > 800:
        reasons.append("long_request")
    if any(marker in normalized for marker in _HIGH_RISK_MARKERS):
        reasons.append("high_risk_domain_marker")
    return AdaptiveRouteDecision(
        resolved_mode="committee" if reasons else "critic",
        reason_codes=list(dict.fromkeys(reasons)) or ["ordinary_request"],
    )


def _constraint_first_answer(
    baseline: str,
    *,
    constraints: list[str],
    required_sections: list[str],
) -> str:
    checks = "; ".join(constraints) or "no caller-supplied hard constraints"
    sections = "; ".join(required_sections) or "no caller-supplied required sections"
    return (
        "Constraint review: "
        f"{checks}. Required sections: {sections}.\n"
        f"{baseline}"
    )


def _skeptical_answer(baseline: str) -> str:
    return (
        f"{baseline}\n"
        "Limitations: this deterministic committee does not prove live-provider quality, "
        "current external facts, public deployment, or production readiness."
    )


def _selection_key(proposal: CommitteeProposal) -> tuple[int, int, int, int]:
    return (
        proposal.hard_reject_count,
        proposal.total_energy,
        _DECISION_ORDER.get(proposal.decision, 99),
        _ROLE_ORDER[proposal.role],
    )


def _approx_tokens(value: str) -> int:
    return max(1, (len(value) + 3) // 4)
