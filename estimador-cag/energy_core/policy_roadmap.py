from __future__ import annotations

from pathlib import Path
from typing import Any

from energy_core.critic_coverage import build_critic_coverage

ROADMAP_VERSION = "1.0.0"

POLICY_ONLY_ROADMAP: dict[str, dict[str, str]] = {
    "unsafe_command": {
        "boundary": "No executor exists in the judge layer.",
        "unblocker": (
            "Add a command proposal model and command safety critic before "
            "any executor exists."
        ),
        "future_evidence": "command_policy_report",
        "slice": "command-safety-proposal-gate",
    },
    "wrong_branch": {
        "boundary": "No git branch reader exists in the judge layer.",
        "unblocker": (
            "Add a read-only repository state provider that reports current "
            "branch and target branch."
        ),
        "future_evidence": "repository_state_report",
        "slice": "repository-state-reader",
    },
    "leaked_proprietary_code": {
        "boundary": "No provenance or license scanner exists in the judge layer.",
        "unblocker": (
            "Add a source provenance input and deterministic scanner result "
            "contract."
        ),
        "future_evidence": "provenance_scan_report",
        "slice": "provenance-and-license-critic",
    },
    "executor_self_approved": {
        "boundary": "No executor role exists in the judge layer.",
        "unblocker": (
            "Add actor role metadata and require approval from a different "
            "critic or decider role."
        ),
        "future_evidence": "role_separation_report",
        "slice": "role-separation-check",
    },
}


def build_policy_roadmap(policy_path: Path) -> dict[str, Any]:
    """Build a roadmap for policy-only constraints without executing adapters."""

    coverage = build_critic_coverage(policy_path)
    policy_only_ids = coverage["policy_only_constraint_ids"]
    entries = [_entry(constraint_id) for constraint_id in policy_only_ids]
    missing_roadmap = [
        constraint_id
        for constraint_id in policy_only_ids
        if constraint_id not in POLICY_ONLY_ROADMAP
    ]

    return {
        "roadmap_version": ROADMAP_VERSION,
        "policy_id": coverage["policy_id"],
        "policy_version": coverage["policy_version"],
        "complete": coverage["complete"] and not missing_roadmap,
        "coverage_level": coverage["coverage_level"],
        "policy_only_total": len(policy_only_ids),
        "enforced_total": coverage["enforced_total"],
        "constraint_total": coverage["constraint_total"],
        "missing_roadmap": missing_roadmap,
        "entries": entries,
        "execution_boundaries": [entry["boundary"] for entry in entries],
        "non_goals": [
            "Policy roadmap does not execute shell actions.",
            "Policy roadmap does not read live git state.",
            "Policy roadmap does not call LLM providers.",
            "Policy roadmap does not approve adapter execution.",
            "Policy roadmap turns policy-only constraints into future slices.",
        ],
    }


def format_policy_roadmap_text(roadmap: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Policy Roadmap",
            f"Roadmap version: {roadmap['roadmap_version']}",
            f"Policy: {roadmap['policy_id']} {roadmap['policy_version']}",
            f"Complete: {roadmap['complete']}",
            f"Coverage level: {roadmap['coverage_level']}",
            f"Policy-only constraints: {roadmap['policy_only_total']}",
            f"Missing roadmap: {_inline_list(roadmap['missing_roadmap'])}",
        ]
    )


def format_policy_roadmap_markdown(roadmap: dict[str, Any]) -> str:
    lines = [
        "# Energy Aware Code Policy Roadmap",
        "",
        f"- Roadmap version: {roadmap['roadmap_version']}",
        f"- Policy: {roadmap['policy_id']}",
        f"- Policy version: {roadmap['policy_version']}",
        f"- Complete: {roadmap['complete']}",
        f"- Coverage level: {roadmap['coverage_level']}",
        f"- Enforced constraints: {roadmap['enforced_total']}/{roadmap['constraint_total']}",
        f"- Policy-only constraints: {roadmap['policy_only_total']}",
        "",
        "## Missing roadmap entries",
        "",
    ]
    lines.extend(_bullet_list(roadmap["missing_roadmap"]))
    lines.extend(["", "## Policy-only roadmap", ""])
    for entry in roadmap["entries"]:
        lines.extend(
            [
                f"### {entry['constraint_id']}",
                "",
                f"- Boundary: {entry['boundary']}",
                f"- Unblocker: {entry['unblocker']}",
                f"- Future evidence: {entry['future_evidence']}",
                f"- Future slice: {entry['slice']}",
                "",
            ]
        )
    lines.extend(["## Execution boundaries", ""])
    lines.extend(_bullet_list(roadmap["execution_boundaries"]))
    lines.extend(["", "## Non goals", ""])
    lines.extend(_bullet_list(roadmap["non_goals"]))
    return "\n".join(lines)


def _entry(constraint_id: str) -> dict[str, str]:
    fallback = {
        "boundary": "No deterministic implementation boundary is registered yet.",
        "unblocker": "Add a deterministic critic mapping before claiming enforcement.",
        "future_evidence": "critic_mapping_report",
        "slice": "critic-mapping-repair",
    }
    return {
        "constraint_id": constraint_id,
        **POLICY_ONLY_ROADMAP.get(constraint_id, fallback),
    }


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]
