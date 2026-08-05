"""Decision rules for Energy Aware Chat."""

from __future__ import annotations

from app.energy_chat.contracts import EnergyDecision, EnergyPolicy, EnergyScore


def decide(score: EnergyScore, policy: EnergyPolicy, evidence_refs: list[str]) -> EnergyDecision:
    """Apply deterministic decider precedence to an energy score."""

    required_repairs = [finding.repair_hint for finding in score.findings]

    if policy.reject_on_any_hard_reject and score.hard_reject_violations:
        return EnergyDecision(
            decision="reject",
            energy=score.total_energy,
            reasoning_summary="At least one hard reject constraint failed.",
            required_repairs=required_repairs,
            evidence_refs=evidence_refs,
        )

    if "insufficient_user_intent" in score.hard_repair_violations:
        return EnergyDecision(
            decision="clarify",
            energy=score.total_energy,
            reasoning_summary="The user intent is insufficient for a safe, useful answer.",
            required_repairs=required_repairs,
            evidence_refs=evidence_refs,
        )

    if score.hard_repair_violations:
        return EnergyDecision(
            decision="repair",
            energy=score.total_energy,
            reasoning_summary="Hard repair constraints failed and the draft needs revision.",
            required_repairs=required_repairs,
            evidence_refs=evidence_refs,
        )

    if score.total_energy >= policy.repair_min_energy:
        return EnergyDecision(
            decision="repair",
            energy=score.total_energy,
            reasoning_summary="Soft constraint energy is above the repair threshold.",
            required_repairs=required_repairs,
            evidence_refs=evidence_refs,
        )

    return EnergyDecision(
        decision="accept",
        energy=score.total_energy,
        reasoning_summary="Hard constraints passed and energy is within the accept threshold.",
        required_repairs=[],
        evidence_refs=evidence_refs,
    )
