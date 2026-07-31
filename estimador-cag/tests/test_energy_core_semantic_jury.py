from decimal import Decimal

import pytest
from pydantic import ValidationError

from energy_core.semantic_jury import (
    ActionGovernor,
    DeterministicHardGateResult,
    HardGateFinding,
    MetaJudgeResult,
    SemanticJudgeResult,
    SemanticJury,
)


def _judge(judge_id: str, disposition: str = "accept") -> SemanticJudgeResult:
    return SemanticJudgeResult(
        judge_id=judge_id,
        provider="fixture",
        model="deterministic-fixture",
        disposition=disposition,
        rubric_scores={"correctness": Decimal("0.8")},
        summary=f"{judge_id} assessment",
        evidence_refs=("proposal-1",),
    )


def test_hard_failure_cannot_be_outvoted_or_arbitrated() -> None:
    hard_gate = DeterministicHardGateResult(
        candidate_id="candidate-1",
        findings=(
            HardGateFinding(
                finding_id="secret",
                constraint="secrets",
                status="fail",
                summary="Secret detected.",
            ),
        ),
    )
    jury = SemanticJury().aggregate((_judge("judge-a"), _judge("judge-b")))
    meta = MetaJudgeResult(
        judge_id="meta-a", disposition="accept", summary="Semantic majority accepts."
    )

    decision = ActionGovernor().decide(hard_gate=hard_gate, jury=jury, meta_judge=meta)

    assert decision.disposition == "reject"
    assert decision.authorized is False
    assert decision.decided_by == "deterministic-action-governor"


def test_jury_requires_independent_judge_identities() -> None:
    with pytest.raises(ValueError, match="independent"):
        SemanticJury().aggregate((_judge("same"), _judge("same")))


def test_disagreement_is_preserved_and_requires_repair() -> None:
    jury = SemanticJury().aggregate((_judge("judge-a"), _judge("judge-b", "repair")))

    decision = ActionGovernor().decide(
        hard_gate=DeterministicHardGateResult(candidate_id="candidate-1"), jury=jury
    )

    assert jury.disagreement is True
    assert jury.positions == ("accept", "repair")
    assert decision.disposition == "repair"


def test_judge_contract_has_no_authorization_field() -> None:
    with pytest.raises(ValidationError):
        SemanticJudgeResult.model_validate(
            {
                **_judge("judge-a").model_dump(),
                "authorized": True,
            }
        )


def test_human_review_action_never_self_authorizes() -> None:
    jury = SemanticJury().aggregate((_judge("judge-a"), _judge("judge-b")))
    decision = ActionGovernor().decide(
        hard_gate=DeterministicHardGateResult(
            candidate_id="candidate-1", human_review_required=True
        ),
        jury=jury,
    )

    assert decision.disposition == "escalate"
    assert decision.authorized is False
    assert decision.human_review_required is True
