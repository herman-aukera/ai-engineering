from app.energy_chat.contracts import CriticFinding
from app.energy_chat.scorer import score_findings


def test_score_splits_hard_and_soft_violations() -> None:
    findings = [
        CriticFinding(
            critic="test",
            violation_id="fabricated_citation",
            constraint_type="hard_reject",
            penalty=1000,
            evidence="citation without evidence",
            repair_hint="remove fabricated citation",
        ),
        CriticFinding(
            critic="test",
            violation_id="weak_structure",
            constraint_type="soft",
            penalty=80,
            evidence="weak structure",
            repair_hint="add structure",
        ),
    ]

    score = score_findings(findings)

    assert score.total_energy == 1080
    assert score.hard_reject_violations == ["fabricated_citation"]
    assert score.soft_violations == ["weak_structure"]
