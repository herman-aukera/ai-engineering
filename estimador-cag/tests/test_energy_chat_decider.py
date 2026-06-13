from app.energy_chat.contracts import ConstraintType, CriticFinding, DecisionType
from app.energy_chat.decider import decide
from app.energy_chat.scorer import score_findings


def test_decider_rejects_when_any_hard_reject_finding_exists():
    findings = [
        CriticFinding(
            critic="claim_critic",
            finding_id="unverified_success_claim",
            constraint_type=ConstraintType.HARD_REJECT,
            energy=900,
            message="The answer claims validation without evidence.",
        )
    ]

    decision = decide(score_findings(findings), findings)

    assert decision.decision == DecisionType.REJECT
    assert decision.hard_constraints_passed is False
    assert decision.next_action == "remove_blocking_violation"


def test_decider_clarifies_when_intent_is_insufficient():
    findings = [
        CriticFinding(
            critic="instruction_critic",
            finding_id="insufficient_user_intent",
            constraint_type=ConstraintType.HARD_REPAIR,
            energy=400,
            message="The user intent is too ambiguous.",
            suggested_decision=DecisionType.CLARIFY,
        )
    ]

    decision = decide(score_findings(findings), findings)

    assert decision.decision == DecisionType.CLARIFY
    assert decision.repairs_required == ["Ask a focused clarification question."]


def test_decider_repairs_hard_repair_findings():
    findings = [
        CriticFinding(
            critic="evidence_critic",
            finding_id="unverified_production_claim",
            constraint_type=ConstraintType.HARD_REPAIR,
            energy=700,
            message="The answer claims production readiness without evidence.",
            repair_hint="Add evidence or remove the claim.",
        )
    ]

    decision = decide(score_findings(findings), findings)

    assert decision.decision == DecisionType.REPAIR
    assert decision.repairs_required == ["Add evidence or remove the claim."]


def test_decider_accepts_low_energy_candidate():
    decision = decide(score_findings([]), [])

    assert decision.decision == DecisionType.ACCEPT
    assert decision.energy == 0
    assert decision.hard_constraints_passed is True
