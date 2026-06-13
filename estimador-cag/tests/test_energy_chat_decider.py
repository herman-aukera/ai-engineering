from app.energy_chat.contracts import CriticFinding, EnergyPolicy
from app.energy_chat.decider import decide
from app.energy_chat.scorer import score_findings


def test_soft_constraints_cannot_override_hard_reject() -> None:
    score = score_findings(
        [
            CriticFinding(
                critic="minimal_safety_critic",
                violation_id="fabricated_citation",
                constraint_type="hard_reject",
                penalty=1000,
                evidence="fake citation",
                repair_hint="remove fake citation",
            ),
            CriticFinding(
                critic="structure_critic",
                violation_id="weak_structure",
                constraint_type="soft",
                penalty=80,
                evidence="weak structure",
                repair_hint="add structure",
            ),
        ]
    )

    decision = decide(score, EnergyPolicy(), [])

    assert decision.decision == "reject"


def test_insufficient_user_intent_returns_clarify() -> None:
    score = score_findings(
        [
            CriticFinding(
                critic="instruction_critic",
                violation_id="insufficient_user_intent",
                constraint_type="hard_repair",
                penalty=300,
                evidence="vague user request",
                repair_hint="ask one clarifying question",
            )
        ]
    )

    decision = decide(score, EnergyPolicy(), [])

    assert decision.decision == "clarify"
