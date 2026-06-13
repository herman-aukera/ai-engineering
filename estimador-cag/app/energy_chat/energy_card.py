from app.energy_chat.contracts import EnergyCard, EnergyDecision


def build_energy_card(decision: EnergyDecision) -> EnergyCard:
    """Create the visible Energy Card from the internal decision record."""

    return EnergyCard(
        decision=decision.decision,
        energy=decision.energy,
        hard_constraints_passed=decision.hard_constraints_passed,
        repairs=len(decision.repairs_required),
        evidence=[f"critic:{finding.finding_id}" for finding in decision.findings],
        remaining_caveats=[finding.message for finding in decision.findings],
    )
