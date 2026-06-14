from __future__ import annotations

from typing import Any

from energy_core.models import ConstraintPolicy, EnergyPolicy


def build_constraint_index(policy: EnergyPolicy) -> dict[str, Any]:
    """Build a deterministic review index from a typed energy policy."""

    hard_reject = _constraint_rows(policy.hard_constraints, decision="reject")
    hard_repair = _constraint_rows(policy.hard_constraints, decision="repair")
    soft = _constraint_rows(policy.soft_constraints)
    referenced_evidence = sorted(
        {
            evidence_type
            for constraint in [*policy.hard_constraints.values(), *policy.soft_constraints.values()]
            for evidence_type in constraint.required_evidence
        }
        | set(policy.required_acceptance_evidence)
    )
    missing_evidence_types = [
        evidence_type
        for evidence_type in referenced_evidence
        if evidence_type not in policy.evidence_types
    ]
    thresholds_valid = policy.thresholds.accept_max_soft_energy < policy.thresholds.repair_min_soft_energy
    decision_rule_ids = [rule.id for rule in policy.decision_rules]
    duplicate_rule_ids = sorted(
        rule_id for rule_id in set(decision_rule_ids) if decision_rule_ids.count(rule_id) > 1
    )

    complete = not missing_evidence_types and thresholds_valid and not duplicate_rule_ids

    return {
        "policy_id": policy.policy_id,
        "version": policy.version,
        "complete": complete,
        "thresholds_valid": thresholds_valid,
        "thresholds": policy.thresholds.model_dump(mode="json"),
        "counts": {
            "hard_reject": len(hard_reject),
            "hard_repair": len(hard_repair),
            "soft": len(soft),
            "evidence_types": len(policy.evidence_types),
            "required_acceptance_evidence": len(policy.required_acceptance_evidence),
            "decision_rules": len(policy.decision_rules),
        },
        "hard_reject": hard_reject,
        "hard_repair": hard_repair,
        "soft": soft,
        "required_acceptance_evidence": sorted(policy.required_acceptance_evidence),
        "evidence_types": sorted(policy.evidence_types.keys()),
        "missing_evidence_types": missing_evidence_types,
        "decision_rules": [rule.model_dump(mode="json") for rule in policy.decision_rules],
        "duplicate_decision_rule_ids": duplicate_rule_ids,
    }


def format_constraint_index_text(index: dict[str, Any]) -> str:
    lines = [
        "Energy Aware Code Constraint Index",
        f"Policy: {index['policy_id']}",
        f"Version: {index['version']}",
        f"Complete: {index['complete']}",
        f"Thresholds valid: {index['thresholds_valid']}",
        f"Hard reject constraints: {index['counts']['hard_reject']}",
        f"Hard repair constraints: {index['counts']['hard_repair']}",
        f"Soft constraints: {index['counts']['soft']}",
        f"Evidence types: {index['counts']['evidence_types']}",
        "Missing evidence types:",
    ]
    lines.extend(_plain_items(index["missing_evidence_types"]))
    lines.append("Required acceptance evidence:")
    lines.extend(_plain_items(index["required_acceptance_evidence"]))
    return "\n".join(lines)


def format_constraint_index_markdown(index: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Energy Aware Code Constraint Index",
            "",
            f"- Policy: {index['policy_id']}",
            f"- Version: {index['version']}",
            f"- Complete: {index['complete']}",
            f"- Thresholds valid: {index['thresholds_valid']}",
            "",
            "## Counts",
            "",
            f"- Hard reject constraints: {index['counts']['hard_reject']}",
            f"- Hard repair constraints: {index['counts']['hard_repair']}",
            f"- Soft constraints: {index['counts']['soft']}",
            f"- Evidence types: {index['counts']['evidence_types']}",
            f"- Required acceptance evidence: {index['counts']['required_acceptance_evidence']}",
            f"- Decision rules: {index['counts']['decision_rules']}",
            "",
            "## Missing evidence types",
            "",
            *_markdown_items(index["missing_evidence_types"]),
            "",
            "## Required acceptance evidence",
            "",
            *_markdown_items(index["required_acceptance_evidence"]),
            "",
            "## Hard reject constraints",
            "",
            *_constraint_markdown_items(index["hard_reject"]),
            "",
            "## Hard repair constraints",
            "",
            *_constraint_markdown_items(index["hard_repair"]),
            "",
            "## Soft constraints",
            "",
            *_constraint_markdown_items(index["soft"]),
        ]
    )


def _constraint_rows(
    constraints: dict[str, ConstraintPolicy], decision: str | None = None
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for constraint_id, constraint in sorted(constraints.items()):
        if decision is not None and constraint.decision != decision:
            continue
        rows.append(
            {
                "id": constraint_id,
                "decision": constraint.decision,
                "penalty": constraint.penalty,
                "required_evidence": sorted(constraint.required_evidence),
                "repair_hint": constraint.repair_hint,
            }
        )
    return rows


def _plain_items(items: list[str]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- {item}" for item in items]


def _markdown_items(items: list[str]) -> list[str]:
    return _plain_items(items)


def _constraint_markdown_items(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["- none"]
    return [
        f"- {row['id']}: decision={row['decision']}, penalty={row['penalty']}"
        for row in rows
    ]
