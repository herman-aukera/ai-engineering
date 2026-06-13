from app.energy_chat.contracts import ConstraintType, CriticFinding
from app.energy_chat.scorer import score_findings


def test_score_findings_groups_blocking_repair_and_soft_findings():
    findings = [
        CriticFinding(
            critic="credential_critic",
            finding_id="credential_exposure",
            constraint_type=ConstraintType.HARD_REJECT,
            energy=1000,
            message="A credential-like value was found.",
        ),
        CriticFinding(
            critic="evidence_critic",
            finding_id="missing_evidence",
            constraint_type=ConstraintType.HARD_REPAIR,
            energy=700,
            message="Required evidence is missing.",
        ),
        CriticFinding(
            critic="structure_critic",
            finding_id="weak_structure",
            constraint_type=ConstraintType.SOFT,
            energy=40,
            message="The answer is weakly structured.",
        ),
    ]

    score = score_findings(findings)

    assert score.energy == 1740
    assert score.hard_reject_violations == ["credential_exposure"]
    assert score.hard_repair_violations == ["missing_evidence"]
    assert score.soft_violations == ["weak_structure"]
