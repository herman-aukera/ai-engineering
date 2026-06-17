from __future__ import annotations

from pathlib import Path
from typing import Any

from energy_core.command_catalog import build_command_catalog
from energy_core.package_manifest import build_package_manifest, resolve_project_root
from energy_core.review_pack_contract import get_review_pack_artifact_files
from energy_core.reviewer_index import REVIEWER_SECTIONS

SURFACE_CONSISTENCY_VERSION = "1.0.0"

CRITICAL_SURFACES = {
    "acceptance_trace": "acceptance_trace.md",
    "candidate_readiness": "candidate_readiness.md",
    "closeout_pack": "closeout_pack.md",
    "command_catalog": "command_catalog.md",
    "course_boundary": "course_boundary.md",
    "critic_coverage": "critic_coverage.md",
    "demo_walkthrough": "demo_walkthrough.md",
    "export_plan": "export_plan.md",
    "extraction_readiness": "extraction_readiness.md",
    "ledger_integrity": "ledger_integrity.md",
    "nightly_status": "nightly_status.md",
    "package_manifest": "package_manifest.md",
    "release_readiness": "release_readiness.md",
    "review_gap_register": "review_gap_register.md",
    "reviewer_snapshot": "reviewer_snapshot.md",
}

INTRINSIC_SURFACES = {"command_catalog", "reviewer_snapshot"}

PACKAGE_MODULES = {
    "acceptance_trace": "energy_core/acceptance_trace.py",
    "candidate_readiness": "energy_core/candidate_readiness.py",
    "closeout_pack": "energy_core/closeout_pack.py",
    "command_catalog": "energy_core/command_catalog.py",
    "course_boundary": "energy_core/course_boundary.py",
    "critic_coverage": "energy_core/critic_coverage.py",
    "demo_walkthrough": "energy_core/demo_walkthrough.py",
    "export_plan": "energy_core/export_plan.py",
    "extraction_readiness": "energy_core/extraction_readiness.py",
    "ledger_integrity": "energy_core/ledger_integrity.py",
    "nightly_status": "energy_core/nightly_status.py",
    "package_manifest": "energy_core/package_manifest.py",
    "release_readiness": "energy_core/release.py",
    "review_gap_register": "energy_core/review_gap_register.py",
    "reviewer_snapshot": "energy_core/reviewer_index.py",
}


def build_surface_consistency(project_root: Path) -> dict[str, Any]:
    root = resolve_project_root(project_root)
    catalog_ids = {command["id"] for command in build_command_catalog()["commands"]}
    reviewer_ids = {section["id"] for section in REVIEWER_SECTIONS}
    review_pack_files = set(get_review_pack_artifact_files())
    package_files = {
        item["relative_path"]
        for item in build_package_manifest(root)["files"]
        if item["group"] == "package" and item["exists"]
    }

    rows: list[dict[str, Any]] = []
    missing: list[str] = []

    for surface_id, review_pack_file in sorted(CRITICAL_SURFACES.items()):
        module_path = PACKAGE_MODULES[surface_id]
        intrinsic = surface_id in INTRINSIC_SURFACES
        row = {
            "surface_id": surface_id,
            "catalog": intrinsic or surface_id in catalog_ids,
            "reviewer": intrinsic or surface_id in reviewer_ids,
            "review_pack": review_pack_file in review_pack_files,
            "package": module_path in package_files,
            "review_pack_file": review_pack_file,
            "package_module": module_path,
        }
        row["complete"] = all(
            [
                row["catalog"],
                row["reviewer"],
                row["review_pack"],
                row["package"],
            ]
        )
        if not row["complete"]:
            missing.append(surface_id)
        rows.append(row)

    return {
        "surface_consistency_version": SURFACE_CONSISTENCY_VERSION,
        "project_root": str(root),
        "complete": not missing,
        "surface_total": len(rows),
        "complete_surface_total": sum(1 for row in rows if row["complete"]),
        "missing_surface_ids": missing,
        "rows": rows,
        "non_goals": [
            "Surface consistency does not execute shell actions.",
            "Surface consistency does not call LLM providers.",
            "Surface consistency does not append to the decision ledger.",
        ],
    }


def format_surface_consistency_text(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Surface Consistency",
            f"Version: {report['surface_consistency_version']}",
            f"Complete: {report['complete']}",
            f"Surfaces: {report['complete_surface_total']}/{report['surface_total']}",
            f"Missing: {_inline_list(report['missing_surface_ids'])}",
        ]
    )


def format_surface_consistency_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Energy Aware Code Surface Consistency",
        "",
        f"- Version: {report['surface_consistency_version']}",
        f"- Project root: {report['project_root']}",
        f"- Complete: {report['complete']}",
        f"- Surfaces: {report['complete_surface_total']}/{report['surface_total']}",
        "",
        "## Missing surfaces",
        "",
    ]
    lines.extend(_bullet_list(report["missing_surface_ids"]))
    lines.extend(["", "## Rows", ""])
    for row in report["rows"]:
        lines.extend(
            [
                f"### {row['surface_id']}",
                "",
                f"- Complete: {row['complete']}",
                f"- Command catalog: {row['catalog']}",
                f"- Reviewer snapshot: {row['reviewer']}",
                f"- Review pack: {row['review_pack']}",
                f"- Package manifest: {row['package']}",
                f"- Review pack file: {row['review_pack_file']}",
                f"- Package module: {row['package_module']}",
                "",
            ]
        )
    lines.extend(["## Non goals", ""])
    lines.extend(_bullet_list(report["non_goals"]))
    return "\n".join(lines)


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items if item] or ["- none"]
