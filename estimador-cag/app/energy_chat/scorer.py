"""Energy scoring for deterministic Energy Aware Chat findings."""

from __future__ import annotations

from app.energy_chat.contracts import CriticFinding, EnergyScore


def score_findings(findings: list[CriticFinding]) -> EnergyScore:
    """Aggregate critic findings into an energy score."""

    hard_reject = [f.violation_id for f in findings if f.constraint_type == "hard_reject"]
    hard_repair = [f.violation_id for f in findings if f.constraint_type == "hard_repair"]
    soft = [f.violation_id for f in findings if f.constraint_type == "soft"]
    return EnergyScore(
        total_energy=sum(f.penalty for f in findings),
        hard_reject_violations=hard_reject,
        hard_repair_violations=hard_repair,
        soft_violations=soft,
        findings=findings,
    )
