from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from energy_core.command_catalog import build_command_catalog
from energy_core.evidence import read_evidence_records
from energy_core.package_manifest import build_package_manifest, resolve_project_root
from energy_core.policy import load_policy

NIGHTLY_STATUS_VERSION = "1.0.0"
DEFAULT_SPEC_DIR = Path(".energy/specs/0001-energy-policy-ledger")
DEFAULT_POLICY = DEFAULT_SPEC_DIR / "energy-policy.yaml"
DEFAULT_EVIDENCE = DEFAULT_SPEC_DIR / "evidence.jsonl"


def build_nightly_status(project_root: Path) -> dict[str, Any]:
    """Build a five-section non-mutating overnight review status pack."""

    root = resolve_project_root(project_root)
    policy = load_policy(root / DEFAULT_POLICY)
    evidence = read_evidence_records(root / DEFAULT_EVIDENCE)
    package_manifest = build_package_manifest(root)
    command_catalog = build_command_catalog()

    policy_section = _policy_health(policy)
    evidence_section = _evidence_completeness(policy, evidence)
    command_section = _command_safety_surface(command_catalog)
    release_section = _release_export_readiness(package_manifest)
    handoff_section = _maintainer_handoff()
    sections = [
        policy_section,
        evidence_section,
        command_section,
        release_section,
        handoff_section,
    ]

    return {
        "nightly_status_version": NIGHTLY_STATUS_VERSION,
        "project_root": str(root),
        "complete": all(section["complete"] for section in sections),
        "section_total": len(sections),
        "section_complete_total": sum(1 for section in sections if section["complete"]),
        "sections": sections,
        "non_goals": [
            "Nightly status does not execute shell actions.",
            "Nightly status does not call LLM providers.",
            "Nightly status does not approve adapter execution.",
            "Nightly status does not append to the decision ledger.",
        ],
    }


def format_nightly_status_text(status: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Nightly Status",
            f"Version: {status['nightly_status_version']}",
            f"Project root: {status['project_root']}",
            f"Complete: {status['complete']}",
            f"Sections: {status['section_complete_total']}/{status['section_total']}",
        ]
    )


def format_nightly_status_markdown(status: dict[str, Any]) -> str:
    lines = [
        "# Energy Aware Code Nightly Status",
        "",
        f"- Version: {status['nightly_status_version']}",
        f"- Project root: {status['project_root']}",
        f"- Complete: {status['complete']}",
        f"- Sections: {status['section_complete_total']}/{status['section_total']}",
        "",
        "## Sections",
        "",
    ]
    for section in status["sections"]:
        lines.extend(
            [
                f"### {section['title']}",
                "",
                f"- Id: {section['id']}",
                f"- Complete: {section['complete']}",
                f"- Summary: {section['summary']}",
                "",
                "#### Facts",
                "",
            ]
        )
        lines.extend(_bullet_list(section["facts"]))
        lines.extend(["", "#### Follow up", ""])
        lines.extend(_bullet_list(section["follow_up"]))
        lines.append("")
    lines.extend(["## Non goals", ""])
    lines.extend(_bullet_list(status["non_goals"]))
    return "\n".join(lines)


def _policy_health(policy: Any) -> dict[str, Any]:
    hard_count = len(policy.hard_constraints)
    soft_count = len(policy.soft_constraints)
    evidence_type_ids = set(policy.evidence_types)
    required_evidence_ids = set(policy.required_acceptance_evidence)
    undeclared_required = sorted(required_evidence_ids - evidence_type_ids)
    thresholds_valid = (
        policy.thresholds.accept_max_soft_energy
        < policy.thresholds.repair_min_soft_energy
    )
    complete = not undeclared_required and thresholds_valid and hard_count > 0

    return {
        "id": "policy_health",
        "title": "M1 Policy health",
        "complete": complete,
        "summary": "Policy structure and threshold declarations are internally consistent.",
        "facts": [
            f"Policy: {policy.policy_id} {policy.version}",
            f"Hard constraints: {hard_count}",
            f"Soft constraints: {soft_count}",
            f"Evidence types: {len(evidence_type_ids)}",
            f"Required acceptance evidence: {len(required_evidence_ids)}",
            f"Thresholds valid: {thresholds_valid}",
            f"Undeclared required evidence: {_inline_list(undeclared_required)}",
        ],
        "follow_up": [
            "Keep policy-only constraints explicit until execution adapters exist.",
        ],
    }


def _evidence_completeness(policy: Any, evidence: list[Any]) -> dict[str, Any]:
    required = list(policy.required_acceptance_evidence)
    statuses_by_type: dict[str, set[str]] = {evidence_type: set() for evidence_type in required}
    trusted_pass_types: set[str] = set()
    for record in evidence:
        statuses_by_type.setdefault(record.type, set()).add(record.status)
        if record.trusted and record.status == "pass":
            trusted_pass_types.add(record.type)

    missing_trusted_pass = [item for item in required if item not in trusted_pass_types]
    status_counts = Counter(record.status for record in evidence)
    complete = not missing_trusted_pass

    return {
        "id": "evidence_completeness",
        "title": "M2 Evidence completeness",
        "complete": complete,
        "summary": "Required acceptance evidence has trusted passing records.",
        "facts": [
            f"Evidence records: {len(evidence)}",
            f"Status counts: {dict(sorted(status_counts.items()))}",
            f"Required evidence: {_inline_list(required)}",
            f"Missing trusted pass evidence: {_inline_list(missing_trusted_pass)}",
        ],
        "follow_up": [
            "Refresh evidence.jsonl after real validation commands change.",
        ],
    }


def _command_safety_surface(catalog: dict[str, Any]) -> dict[str, Any]:
    mutating = catalog["mutating_command_ids"]
    unsupported_root = catalog["unsupported_root_command_ids"]
    complete = len(mutating) == 1 and mutating == ["evaluate"] and not unsupported_root

    return {
        "id": "command_safety_surface",
        "title": "M3 Command safety surface",
        "complete": complete,
        "summary": "Public commands are cataloged with mutation and root-support metadata.",
        "facts": [
            f"Commands: {catalog['command_total']}",
            f"Mutating commands: {_inline_list(mutating)}",
            f"Dry-run commands: {_inline_list(catalog['dry_run_command_ids'])}",
            f"Repo-root supported: {catalog['repo_root_supported']}",
            f"Unsupported root commands: {_inline_list(unsupported_root)}",
        ],
        "follow_up": [
            "Any future executor command must be added as mutating and separately gated.",
        ],
    }


def _release_export_readiness(package_manifest: dict[str, Any]) -> dict[str, Any]:
    complete = package_manifest["complete"]
    return {
        "id": "release_export_readiness",
        "title": "M4 Release/export readiness",
        "complete": complete,
        "summary": "Extraction inventory is complete for the current incubator package.",
        "facts": [
            f"Package manifest complete: {complete}",
            "Present files: "
            f"{package_manifest['present_total']}/{package_manifest['required_total']}",
            "Missing required: "
            f"{_inline_list(package_manifest['missing_required'])}",
        ],
        "follow_up": [
            "Run export-plan and scaffold before creating a standalone repository.",
        ],
    }


def _maintainer_handoff() -> dict[str, Any]:
    commands = [
        "python -m energy_core.nightly_status_cli --format markdown",
        "python -m energy_core.review_pack_cli --format markdown --fail-on-incomplete",
        "python scripts/energy_core_full_gate.py --fix",
    ]
    return {
        "id": "maintainer_handoff",
        "title": "M5 Maintainer handoff",
        "complete": True,
        "summary": "A maintainer can review status, artifacts, and gates from three commands.",
        "facts": [f"Command: {command}" for command in commands],
        "follow_up": [
            "Use this section as the first checkpoint after an overnight batch.",
        ],
    }


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]
