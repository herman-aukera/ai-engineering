from app.energy_chat.contracts import (
    ConstraintType,
    CriticFinding,
    DecisionType,
    EnergyDecision,
    EnergyScore,
)

ACCEPT_MAX_ENERGY = 120


def decide(score: EnergyScore, findings: list[CriticFinding]) -> EnergyDecision:
    """Apply deterministic decision precedence to a scored candidate answer."""

    if score.hard_reject_violations:
        return EnergyDecision(
            decision=DecisionType.REJECT,
            energy=score.energy,
            hard_constraints_passed=False,
            repairs_required=_repair_hints(findings),
            findings=findings,
            reasoning_summary="The candidate answer has a blocking hard constraint violation.",
            next_action="remove_blocking_violation",
        )

    clarify_finding = next(
        (
            finding
            for finding in findings
            if finding.suggested_decision == DecisionType.CLARIFY
        ),
        None,
    )
    if clarify_finding is not None:
        return EnergyDecision(
            decision=DecisionType.CLARIFY,
            energy=score.energy,
            hard_constraints_passed=True,
            repairs_required=[clarify_finding.repair_hint or "Ask a focused clarification question."],
            findings=findings,
            reasoning_summary="The candidate needs clarification before a reliable answer is possible.",
            next_action="ask_clarifying_question",
        )

    hard_repairs = [
        finding for finding in findings if finding.constraint_type == ConstraintType.HARD_REPAIR
    ]
    if hard_repairs:
        return EnergyDecision(
            decision=DecisionType.REPAIR,
            energy=score.energy,
            hard_constraints_passed=True,
            repairs_required=_repair_hints(hard_repairs),
            findings=findings,
            reasoning_summary="The candidate can be repaired, but cannot be accepted yet.",
            next_action="repair_candidate_answer",
        )

    if score.energy > ACCEPT_MAX_ENERGY:
        return EnergyDecision(
            decision=DecisionType.REPAIR,
            energy=score.energy,
            hard_constraints_passed=True,
            repairs_required=_repair_hints(findings),
            findings=findings,
            reasoning_summary="Soft constraint energy is above the accept threshold.",
            next_action="repair_candidate_answer",
        )

    return EnergyDecision(
        decision=DecisionType.ACCEPT,
        energy=score.energy,
        hard_constraints_passed=True,
        repairs_required=[],
        findings=findings,
        reasoning_summary="Hard constraints passed and energy is below the accept threshold.",
        next_action="return_answer",
    )


def _repair_hints(findings: list[CriticFinding]) -> list[str]:
    hints = [finding.repair_hint for finding in findings if finding.repair_hint]
    return hints or ["Repair the candidate answer according to critic findings."]
