from __future__ import annotations

from pathlib import Path
from typing import Any

from energy_core.package_manifest import build_package_manifest, resolve_project_root

SNAPSHOT_VERSION = "1.0.0"
REVIEWER_SECTIONS = [
    {
        "id": "release_readiness",
        "title": "Release readiness",
        "command": "python -m energy_core.release_cli --format markdown --fail-on-not-ready",
        "purpose": "Proves the incubator is ready for future extraction review.",
    },
    {
        "id": "package_manifest",
        "title": "Package manifest",
        "command": "python -m energy_core.package_cli --format markdown --fail-on-incomplete",
        "purpose": "Lists copy roots, required artifacts, hashes, and non-goals.",
    },
    {
        "id": "export_plan",
        "title": "Export plan",
        "command": "python -m energy_core.export_plan_cli --format markdown --fail-on-not-ready",
        "purpose": "Lists future standalone extraction copy items and excluded incubator-only files.",
    },
    {
        "id": "audit_pack",
        "title": "Audit pack",
        "command": "python -m energy_core.cli audit-pack --format markdown --fail-on-not-ready",
        "purpose": "Combines spec, policy, candidate, evidence, decision preview, and ledger status.",
    },
    {
        "id": "schema_bundle",
        "title": "Schema bundle",
        "command": "python -m energy_core.schema_cli --format text",
        "purpose": "Shows machine-readable contracts for candidates, evidence, policy, violations, and decisions.",
    },
    {
        "id": "command_catalog",
        "title": "Command catalog",
        "command": "python -m energy_core.command_catalog_cli --format markdown --fail-on-incomplete",
        "purpose": "Lists supported commands, mutation behavior, root support, and smoke coverage.",
    },
    {
        "id": "critic_coverage",
        "title": "Critic coverage",
        "command": "python -m energy_core.critic_coverage_cli --format markdown --fail-on-unclassified",
        "purpose": "Shows which policy constraints are enforced by deterministic critics versus policy-only.",
    },
    {
        "id": "example_matrix",
        "title": "Example matrix",
        "command": "python -m energy_core.examples_cli --format markdown --fail-on-mismatch",
        "purpose": "Proves bundled examples still match expected policy decisions.",
    },
    {
        "id": "constraint_index",
        "title": "Constraint index",
        "command": "python -m energy_core.constraints_cli --format markdown --fail-on-incomplete",
        "purpose": "Exposes hard reject, hard repair, soft constraints, evidence types, and decision rules.",
    },
    {
        "id": "review_pack",
        "title": "Review pack",
        "command": "python -m energy_core.review_pack_cli --format markdown --fail-on-incomplete",
        "purpose": "Exports a generated Markdown review folder for humans.",
    },
    {
        "id": "scaffold",
        "title": "Standalone scaffold",
        "command": "python -m energy_core.scaffold_cli --format markdown --fail-on-incomplete",
        "purpose": "Generates a non-copying standalone repository scaffold.",
    },
    {
        "id": "smoke_suite",
        "title": "Smoke suite",
        "command": "python scripts/energy_core_full_gate.py",
        "purpose": "Runs the human-facing CLI paths that reviewers are expected to trust.",
    },
]


def build_reviewer_snapshot(project_root: Path) -> dict[str, Any]:
    root = resolve_project_root(project_root)
    package_manifest = build_package_manifest(root)
    present_sections = [section["id"] for section in REVIEWER_SECTIONS]

    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "project_root": str(root),
        "complete": package_manifest["complete"] and len(present_sections) == len(REVIEWER_SECTIONS),
        "section_total": len(REVIEWER_SECTIONS),
        "section_present_total": len(present_sections),
        "sections": REVIEWER_SECTIONS,
        "package_manifest_complete": package_manifest["complete"],
        "package_manifest_present_files": package_manifest["present_total"],
        "package_manifest_required_files": package_manifest["required_total"],
        "reviewer_use": [
            "Show this snapshot before asking a human to inspect individual command outputs.",
            "Use package-manifest for copy/extraction inventory.",
            "Use export-plan for future standalone extraction planning.",
            "Use release-readiness for final extraction gate status.",
            "Use audit-pack when reviewing one candidate state against policy and evidence.",
            "Use command-catalog to understand which commands mutate the ledger.",
            "Use critic-coverage to see which constraints are enforced versus policy-only.",
        ],
        "non_goals": [
            "This snapshot does not execute shell actions.",
            "This snapshot does not call LLM providers.",
            "This snapshot does not approve adapter execution.",
        ],
    }


def format_reviewer_snapshot_text(snapshot: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Reviewer Snapshot",
            f"Snapshot version: {snapshot['snapshot_version']}",
            f"Project root: {snapshot['project_root']}",
            f"Complete: {snapshot['complete']}",
            f"Sections: {snapshot['section_present_total']}/{snapshot['section_total']}",
            f"Package manifest complete: {snapshot['package_manifest_complete']}",
        ]
    )


def format_reviewer_snapshot_markdown(snapshot: dict[str, Any]) -> str:
    lines = [
        "# Energy Aware Code Reviewer Snapshot",
        "",
        f"- Snapshot version: {snapshot['snapshot_version']}",
        f"- Project root: {snapshot['project_root']}",
        f"- Complete: {snapshot['complete']}",
        f"- Sections: {snapshot['section_present_total']}/{snapshot['section_total']}",
        f"- Package manifest complete: {snapshot['package_manifest_complete']}",
        f"- Package files: {snapshot['package_manifest_present_files']}/{snapshot['package_manifest_required_files']}",
        "",
        "## Reviewer sections",
        "",
    ]
    for section in snapshot["sections"]:
        lines.extend(
            [
                f"### {section['title']}",
                "",
                f"- Id: {section['id']}",
                f"- Command: `{section['command']}`",
                f"- Purpose: {section['purpose']}",
                "",
            ]
        )
    lines.extend(["## Reviewer use", ""])
    lines.extend(f"- {item}" for item in snapshot["reviewer_use"])
    lines.extend(["", "## Non goals", ""])
    lines.extend(f"- {item}" for item in snapshot["non_goals"])
    return "\n".join(lines)
