from __future__ import annotations

from energy_core.models import EnergyDecision


def format_decision_summary(decision: EnergyDecision) -> str:
    return (
        f"{decision.decision.upper()} candidate={decision.candidate_id} "
        f"energy={decision.energy_after} delta={decision.energy_delta} "
        f"next={decision.next_action}"
    )
