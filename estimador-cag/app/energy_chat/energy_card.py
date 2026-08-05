"""Energy Card generation for user-visible evaluation summaries."""

from __future__ import annotations

from app.energy_chat.contracts import EnergyCard, EnergyDecision, EnergyScore


def build_energy_card(decision: EnergyDecision, score: EnergyScore) -> EnergyCard:
    """Build the compact Energy Card shown beside an evaluated answer."""

    caveats = [finding.evidence for finding in score.findings if finding.constraint_type != "hard_reject"]
    return EnergyCard(
        decision=decision.decision,
        energy=decision.energy,
        hard_constraints_passed=not score.hard_reject_violations,
        repairs=len(decision.required_repairs),
        evidence=decision.evidence_refs or ["policy", "critic_results"],
        remaining_caveats=caveats,
    )
