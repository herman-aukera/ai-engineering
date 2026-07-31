"""Typed semantic-quality evidence with deterministic final authority."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Literal

from pydantic import Field

from energy_core.models import EnergyModel

SemanticDisposition = Literal["accept", "repair", "reject", "escalate"]
HardGateStatus = Literal["pass", "fail"]


class HardGateFinding(EnergyModel):
    finding_id: str = Field(min_length=1)
    constraint: str = Field(min_length=1)
    status: HardGateStatus
    summary: str
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)


class DeterministicHardGateResult(EnergyModel):
    candidate_id: str = Field(min_length=1)
    findings: tuple[HardGateFinding, ...] = Field(default_factory=tuple)
    human_review_required: bool = False

    @property
    def passed(self) -> bool:
        return all(finding.status == "pass" for finding in self.findings)


class SemanticJudgeResult(EnergyModel):
    """Untrusted semantic evidence; deliberately contains no authority field."""

    judge_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    disposition: SemanticDisposition
    rubric_scores: dict[str, Decimal] = Field(default_factory=dict)
    summary: str
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)


class JuryResult(EnergyModel):
    results: tuple[SemanticJudgeResult, ...]
    recommended_disposition: SemanticDisposition
    disagreement: bool
    positions: tuple[SemanticDisposition, ...]


class MetaJudgeResult(EnergyModel):
    """Optional arbitration evidence; never authorization."""

    judge_id: str = Field(min_length=1)
    disposition: SemanticDisposition
    summary: str
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)


class GovernorDecision(EnergyModel):
    disposition: SemanticDisposition
    authorized: bool = False
    human_review_required: bool = False
    decided_by: str = "deterministic-action-governor"
    reason: str


class SemanticJury:
    def aggregate(self, results: tuple[SemanticJudgeResult, ...]) -> JuryResult:
        if not results:
            raise ValueError("Semantic jury requires at least one judge result.")
        judge_ids = [result.judge_id for result in results]
        if len(judge_ids) != len(set(judge_ids)):
            raise ValueError("Semantic jury requires independent judge identities.")

        positions = tuple(result.disposition for result in results)
        counts = Counter(positions)
        highest = max(counts.values())
        leaders = [position for position, count in counts.items() if count == highest]
        if len(leaders) != 1:
            recommended: SemanticDisposition = "repair"
        else:
            recommended = leaders[0]
        return JuryResult(
            results=results,
            recommended_disposition=recommended,
            disagreement=len(set(positions)) > 1,
            positions=positions,
        )


class ActionGovernor:
    """Sole deterministic owner of the final disposition."""

    def decide(
        self,
        *,
        hard_gate: DeterministicHardGateResult,
        jury: JuryResult,
        meta_judge: MetaJudgeResult | None = None,
    ) -> GovernorDecision:
        if not hard_gate.passed:
            return GovernorDecision(
                disposition="reject",
                reason="A deterministic hard constraint failed.",
            )
        if hard_gate.human_review_required:
            return GovernorDecision(
                disposition="escalate",
                human_review_required=True,
                reason="Server-owned policy requires human review.",
            )

        semantic = meta_judge.disposition if meta_judge is not None else jury.recommended_disposition
        if jury.disagreement and meta_judge is None and semantic == "accept":
            semantic = "repair"
        return GovernorDecision(
            disposition=semantic,
            reason="Deterministic governor applied hard-gate and semantic evidence policy.",
        )
