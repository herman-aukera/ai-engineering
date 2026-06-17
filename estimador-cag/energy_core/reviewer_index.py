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
        "id": "extraction_readiness",
        "title": "Extraction readiness",
        "command": "python -m energy_core.extraction_readiness_cli --format markdown --fail-on-incomplete",
        "purpose": "Checks whether inventory, reviewer artifacts, consistency, gaps, and closeout handoff support future extraction review.",
    },
    {
        "id": "nightly_status",
        "title": "Nightly status",
        "command": "python -m energy_core.nightly_status_cli --format markdown --fail-on-incomplete",
        "purpose": "Summarizes five overnight maintainer checkpoints in one status surface.",
    },
    {
        "id": "acceptance_trace",
        "title": "Acceptance trace",
        "command": "python -m energy_core.acceptance_trace_cli --format markdown --fail-on-incomplete",
        "purpose": "Traces acceptance criteria to evidence, tests, and reviewer surfaces.",
    },
    {
        "id": "demo_walkthrough",
        "title": "Demo walkthrough",
        "command": "python -m energy_core.demo_walkthrough_cli --format markdown --fail-on-incomplete",
        "purpose": "Gives a human-facing proof order for reviewer demos and portfolio recordings.",
    },
    {
        "id": "course_boundary",
        "title": "Course boundary",
        "command": "python -m energy_core.course_boundary_cli --format markdown --fail-on-conflict",
        "purpose": "Separates EACODE incubation from Session 08, Session 09, Chat, and final-project branch roles.",
    },
    {
        "id": "closeout_pack",
        "title": "Closeout pack",
        "command": "python -m energy_core.closeout_pack_cli --format markdown --fail-on-incomplete",
        "purpose": "Provides an end-of-day handoff across status, evidence, gaps, demo, and next slices.",
    },
    {
        "id": "audit_pack",
        "title": "Audit pack",
        "command": "python -m energy_core.cli audit-pack --format markdown --fail-on-not-ready",
        "purpose": "Combines spec, policy, candidate, evidence, decision preview, and ledger status.",
    },
    {
        "id": "ledger_integrity",
        "title": "Ledger integrity",
        "command": "python -m energy_core.ledger_integrity_cli --format markdown --fail-on-invalid",
        "purpose": "Inspects JSONL decision ledger integrity without mutation.",
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
        "id": "candidate_readiness",
        "title": "Candidate readiness",
        "command": "python -m energy_core.candidate_readiness_cli --format markdown --fail-on-incomplete",
        "purpose": "Shows which bundled candidate examples are structurally ready for judgment.",
    },
    {
        "id": "review_gap_register",
        "title": "Review gap register",
        "command": "python -m energy_core.review_gap_register_cli --format markdown --fail-on-blocking",
        "purpose": "Lists blocking gaps, planned boundaries, and accepted non-blocking review gaps.",
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
            "Use closeout-pack as the last end-of-day handoff before stopping work.",
            "Use extraction-readiness before planning a standalone repository cut.",
            "Use demo-walkthrough to decide the order of a portfolio or teacher demo.",
            "Use course-boundary before mixing EACODE with coursework or final-project branches.",
            "Use nightly-status as the first morning checkpoint after overnight work.",
            "Use acceptance-trace to connect acceptance criteria to evidence and tests.",
            "Use package-manifest for copy/extraction inventory.",
            "Use export-plan for future standalone extraction planning.",
            "Use release-readiness for final extraction gate status.",
            "Use audit-pack when reviewing one candidate state against policy and evidence.",
            "Use ledger-integrity before trusting decision ledger history.",
            "Use command-catalog to understand which commands mutate the ledger.",
            "Use critic-coverage to see which constraints are enforced versus policy-only.",
            "Use candidate-readiness before trusting bundled examples as acceptance cases.",
            "Use review-gap-register to separate blocking defects from accepted boundaries.",
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
