from __future__ import annotations

from collections import Counter
from statistics import mean

from energy_core.models import EnergyDecision


def summarize_decision_trends(decisions: list[EnergyDecision]) -> dict[str, object]:
    """Summarize decision history as deterministic trend data."""

    by_decision = Counter(decision.decision for decision in decisions)
    energies_after = [decision.energy_after for decision in decisions]
    energy_deltas = [decision.energy_delta for decision in decisions]
    non_accept_candidate_ids = [decision.candidate_id for decision in decisions if decision.decision != "accept"]
    regressing_candidate_ids = [decision.candidate_id for decision in decisions if decision.energy_delta > 0]
    improving_candidate_ids = [decision.candidate_id for decision in decisions if decision.energy_delta < 0]
    neutral_candidate_ids = [decision.candidate_id for decision in decisions if decision.energy_delta == 0]
    latest = decisions[-1] if decisions else None

    return {
        "total": len(decisions),
        "by_decision": dict(sorted(by_decision.items())),
        "accepted": by_decision.get("accept", 0),
        "non_accept": len(non_accept_candidate_ids),
        "non_accept_candidate_ids": non_accept_candidate_ids,
        "improving": len(improving_candidate_ids),
        "regressing": len(regressing_candidate_ids),
        "neutral": len(neutral_candidate_ids),
        "improving_candidate_ids": improving_candidate_ids,
        "regressing_candidate_ids": regressing_candidate_ids,
        "neutral_candidate_ids": neutral_candidate_ids,
        "min_energy_after": min(energies_after) if energies_after else None,
        "max_energy_after": max(energies_after) if energies_after else None,
        "average_energy_after": round(mean(energies_after), 2) if energies_after else None,
        "average_energy_delta": round(mean(energy_deltas), 2) if energy_deltas else None,
        "latest_decision": latest.model_dump(mode="json") if latest else None,
        "trend": _trend_label(len(decisions), len(regressing_candidate_ids), len(improving_candidate_ids)),
    }


def format_decision_trends_text(summary: dict[str, object]) -> str:
    latest = summary["latest_decision"]
    latest_line = "none" if latest is None else f"{latest['candidate_id']} -> {latest['decision']}"
    return "\n".join(
        [
            "Energy Aware Code Decision Trends",
            f"Total decisions: {summary['total']}",
            f"Trend: {summary['trend']}",
            f"Accepted: {summary['accepted']}",
            f"Non accept: {summary['non_accept']}",
            f"Improving steps: {summary['improving']}",
            f"Regressing steps: {summary['regressing']}",
            f"Neutral steps: {summary['neutral']}",
            f"Min energy after: {_none(summary['min_energy_after'])}",
            f"Max energy after: {_none(summary['max_energy_after'])}",
            f"Average energy after: {_none(summary['average_energy_after'])}",
            f"Average energy delta: {_none(summary['average_energy_delta'])}",
            f"Latest decision: {latest_line}",
            f"Non accept candidate ids: {_inline_list(summary['non_accept_candidate_ids'])}",
            f"Regressing candidate ids: {_inline_list(summary['regressing_candidate_ids'])}",
        ]
    )


def format_decision_trends_markdown(summary: dict[str, object]) -> str:
    latest = summary["latest_decision"]
    latest_lines = ["- none"]
    if latest is not None:
        latest_lines = [
            f"- Candidate: {latest['candidate_id']}",
            f"- Decision: {latest['decision']}",
            f"- Energy after: {latest['energy_after']}",
            f"- Energy delta: {latest['energy_delta']}",
        ]

    return "\n".join(
        [
            "# Energy Aware Code Decision Trends",
            "",
            f"- Total decisions: {summary['total']}",
            f"- Trend: {summary['trend']}",
            f"- Accepted: {summary['accepted']}",
            f"- Non accept: {summary['non_accept']}",
            f"- Improving steps: {summary['improving']}",
            f"- Regressing steps: {summary['regressing']}",
            f"- Neutral steps: {summary['neutral']}",
            "",
            "## Energy",
            "",
            f"- Min energy after: {_none(summary['min_energy_after'])}",
            f"- Max energy after: {_none(summary['max_energy_after'])}",
            f"- Average energy after: {_none(summary['average_energy_after'])}",
            f"- Average energy delta: {_none(summary['average_energy_delta'])}",
            "",
            "## Latest decision",
            "",
            *latest_lines,
            "",
            "## Non accept candidate ids",
            "",
            *_bullet_list(summary["non_accept_candidate_ids"]),
            "",
            "## Regressing candidate ids",
            "",
            *_bullet_list(summary["regressing_candidate_ids"]),
            "",
        ]
    )


def _trend_label(total: int, regressing: int, improving: int) -> str:
    if total == 0:
        return "empty"
    if regressing > 0:
        return "needs_attention"
    if improving > 0:
        return "improving"
    return "stable"


def _none(value: object) -> object:
    return "none" if value is None else value


def _inline_list(items: object) -> str:
    if not isinstance(items, list) or not items:
        return "none"
    return ", ".join(str(item) for item in items)


def _bullet_list(items: object) -> list[str]:
    if not isinstance(items, list) or not items:
        return ["- none"]
    return [f"- {item}" for item in items]
