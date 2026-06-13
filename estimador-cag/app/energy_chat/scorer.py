from app.energy_chat.contracts import ConstraintType, CriticFinding, EnergyScore


def score_findings(findings: list[CriticFinding]) -> EnergyScore:
    """Convert critic findings into deterministic energy."""

    return EnergyScore(
        energy=sum(finding.energy for finding in findings),
        hard_reject_violations=[
            finding.finding_id
            for finding in findings
            if finding.constraint_type == ConstraintType.HARD_REJECT
        ],
        hard_repair_violations=[
            finding.finding_id
            for finding in findings
            if finding.constraint_type == ConstraintType.HARD_REPAIR
        ],
        soft_violations=[
            finding.finding_id for finding in findings if finding.constraint_type == ConstraintType.SOFT
        ],
    )
