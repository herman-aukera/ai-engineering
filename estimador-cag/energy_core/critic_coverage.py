from __future__ import annotations

from pathlib import Path
from typing import Any

from energy_core.models import ConstraintPolicy
from energy_core.policy import load_policy

COVERAGE_VERSION = "1.0.0"

HARD_ENFORCEMENT: dict[str, tuple[str, str]] = {
    "tests_failed": (
        "gate_critic",
        "Failed pytest_output evidence produces a hard reject violation.",
    ),
    "compile_failed": (
        "gate_critic",
        "Failed compile_output evidence produces a hard reject violation.",
    ),
    "lint_failed": (
        "gate_critic",
        "Failed lint_output evidence produces a hard repair violation.",
    ),
    "secret_leak": (
        "gate_critic",
        "Failed secret_scan_output evidence produces a hard reject violation.",
    ),
    "scope_creep": (
        "scope_critic",
        "Candidate scope claims and out-of-scope artifact paths produce a hard reject violation.",
    ),
    "missing_required_artifact": (
        "artifact_critic",
        "Missing candidate required_artifacts produce a hard repair violation.",
    ),
    "missing_required_evidence": (
        "evidence_critic",
        "Missing policy required_acceptance_evidence produces a hard repair violation.",
    ),
    "unverified_success_claim": (
        "claim_critic",
        "Success claims without trusted acceptance evidence produce a hard reject violation.",
    ),
}

POLICY_ONLY_HARD: dict[str, str] = {
    "unsafe_command": "No shell executor exists yet, so unsafe command checks remain policy-only.",
    "wrong_branch": "No git branch reader exists yet, so branch checks remain policy-only.",
    "leaked_proprietary_code": "No provenance scanner exists yet, so this remains policy-only.",
    "executor_self_approved": "No executor role exists yet, so self-approval checks remain policy-only.",
}

SOFT_ENFORCEMENT = (
    "maintainability_critic",
    "Candidate soft_flags produce soft maintainability violations when present.",
)


def build_critic_coverage(policy_path: Path) -> dict[str, Any]:
    """Classify policy constraints by deterministic critic coverage."""

    policy = load_policy(policy_path)
    hard_rows = [
        _hard_row(constraint_id, constraint)
        for constraint_id, constraint in sorted(policy.hard_constraints.items())
    ]
    soft_rows = [
        _soft_row(constraint_id, constraint)
        for constraint_id, constraint in sorted(policy.soft_constraints.items())
    ]
    rows = hard_rows + soft_rows

    unclassified = [row["constraint_id"] for row in rows if row["coverage"] == "unclassified"]
    policy_only = [row["constraint_id"] for row in rows if row["coverage"] == "policy_only"]
    enforced = [row["constraint_id"] for row in rows if row["coverage"] == "enforced"]

    return {
        "coverage_version": COVERAGE_VERSION,
        "policy_id": policy.policy_id,
        "policy_version": policy.version,
        "complete": not unclassified,
        "coverage_level": "full" if not policy_only and not unclassified else "partial",
        "constraint_total": len(rows),
        "enforced_total": len(enforced),
        "policy_only_total": len(policy_only),
        "unclassified_total": len(unclassified),
        "enforced_constraint_ids": enforced,
        "policy_only_constraint_ids": policy_only,
        "unclassified_constraint_ids": unclassified,
        "rows": rows,
        "non_goals": [
            "Critic coverage does not execute shell actions.",
            "Critic coverage does not call LLM providers.",
            "Critic coverage does not approve adapter execution.",
            "Policy-only constraints are explicit gaps, not hidden success claims.",
        ],
    }


def format_critic_coverage_text(coverage: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Critic Coverage",
            f"Coverage version: {coverage['coverage_version']}",
            f"Policy: {coverage['policy_id']}",
            f"Complete: {coverage['complete']}",
            f"Coverage level: {coverage['coverage_level']}",
            f"Enforced constraints: {coverage['enforced_total']}/{coverage['constraint_total']}",
            f"Policy-only constraints: {_inline_list(coverage['policy_only_constraint_ids'])}",
        ]
    )


def format_critic_coverage_markdown(coverage: dict[str, Any]) -> str:
    lines = [
        "# Energy Aware Code Critic Coverage",
        "",
        f"- Coverage version: {coverage['coverage_version']}",
        f"- Policy: {coverage['policy_id']}",
        f"- Policy version: {coverage['policy_version']}",
        f"- Complete: {coverage['complete']}",
        f"- Coverage level: {coverage['coverage_level']}",
        f"- Enforced constraints: {coverage['enforced_total']}/{coverage['constraint_total']}",
        f"- Policy-only constraints: {coverage['policy_only_total']}",
        f"- Unclassified constraints: {coverage['unclassified_total']}",
        "",
        "## Policy-only constraints",
        "",
    ]
    lines.extend(_bullet_list(coverage["policy_only_constraint_ids"]))
    lines.extend(["", "## Rows", ""])
    for row in coverage["rows"]:
        lines.extend(
            [
                f"### {row['constraint_id']}",
                "",
                f"- Kind: {row['kind']}",
                f"- Policy decision: {row['policy_decision']}",
                f"- Penalty: {row['penalty']}",
                f"- Coverage: {row['coverage']}",
                f"- Critic: {row['critic']}",
                f"- Mechanism: {row['mechanism']}",
                "",
            ]
        )
    lines.extend(["## Non goals", ""])
    lines.extend(_bullet_list(coverage["non_goals"]))
    return "\n".join(lines)


def _hard_row(constraint_id: str, constraint: ConstraintPolicy) -> dict[str, Any]:
    if constraint_id in HARD_ENFORCEMENT:
        critic, mechanism = HARD_ENFORCEMENT[constraint_id]
        coverage = "enforced"
    elif constraint_id in POLICY_ONLY_HARD:
        critic = "policy_only"
        mechanism = POLICY_ONLY_HARD[constraint_id]
        coverage = "policy_only"
    else:
        critic = "unclassified"
        mechanism = "No deterministic critic mapping is declared."
        coverage = "unclassified"

    return _row(
        constraint_id=constraint_id,
        constraint=constraint,
        kind="hard",
        coverage=coverage,
        critic=critic,
        mechanism=mechanism,
    )


def _soft_row(constraint_id: str, constraint: ConstraintPolicy) -> dict[str, Any]:
    critic, mechanism = SOFT_ENFORCEMENT
    return _row(
        constraint_id=constraint_id,
        constraint=constraint,
        kind="soft",
        coverage="enforced",
        critic=critic,
        mechanism=mechanism,
    )


def _row(
    *,
    constraint_id: str,
    constraint: ConstraintPolicy,
    kind: str,
    coverage: str,
    critic: str,
    mechanism: str,
) -> dict[str, Any]:
    return {
        "constraint_id": constraint_id,
        "kind": kind,
        "policy_decision": constraint.decision,
        "penalty": constraint.penalty,
        "coverage": coverage,
        "critic": critic,
        "mechanism": mechanism,
    }


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]
