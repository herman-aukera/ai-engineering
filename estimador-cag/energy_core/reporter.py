from __future__ import annotations

from energy_core.models import EnergyDecision


def format_decision_summary(decision: EnergyDecision) -> str:
    lines = [
        "Energy Aware Code Decision",
        f"Decision: {decision.decision}",
        f"Candidate: {decision.candidate_id}",
        f"Policy: {decision.policy_id}",
        f"Energy: {decision.energy_after}",
        f"Energy before: {decision.energy_before}",
        f"Energy delta: {decision.energy_delta}",
        f"Hard reject violations: {_inline_list(decision.hard_reject_violations)}",
        f"Hard repair violations: {_inline_list(decision.hard_repair_violations)}",
        f"Soft violations: {_inline_list(decision.soft_violations)}",
        f"Missing evidence: {_inline_list(decision.missing_evidence)}",
        "Evidence refs:",
        *_bullet_list(decision.evidence_refs),
        "Required repairs:",
        *_bullet_list(decision.required_repairs),
        f"Reasoning: {decision.reasoning_summary}",
        f"Next action: {decision.next_action}",
    ]
    return "\n".join(lines)


def format_decision_markdown_report(decision: EnergyDecision) -> str:
    sections = [
        "# Energy Aware Code Decision Report",
        "",
        f"Decision: {decision.decision}",
        f"Candidate: {decision.candidate_id}",
        f"Policy: {decision.policy_id}",
        "",
        "## Energy",
        "",
        f"- Energy before: {decision.energy_before}",
        f"- Energy after: {decision.energy_after}",
        f"- Energy delta: {decision.energy_delta}",
        "",
        "## Violations",
        "",
        f"- Hard reject: {_inline_list(decision.hard_reject_violations)}",
        f"- Hard repair: {_inline_list(decision.hard_repair_violations)}",
        f"- Soft: {_inline_list(decision.soft_violations)}",
        f"- Missing evidence: {_inline_list(decision.missing_evidence)}",
        "",
        "## Evidence refs",
        "",
        *_bullet_list(decision.evidence_refs),
        "",
        "## Required repairs",
        "",
        *_bullet_list(decision.required_repairs),
        "",
        "## Reasoning summary",
        "",
        decision.reasoning_summary,
        "",
        "## Next action",
        "",
        decision.next_action,
        "",
    ]
    return "\n".join(sections)


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- {item}" for item in items]
