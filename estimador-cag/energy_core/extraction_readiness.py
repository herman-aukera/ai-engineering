from __future__ import annotations

from pathlib import Path
from typing import Any

from energy_core.closeout_pack import build_closeout_pack
from energy_core.package_manifest import build_package_manifest, resolve_project_root
from energy_core.review_gap_register import build_review_gap_register
from energy_core.review_pack_contract import get_review_pack_artifact_files
from energy_core.surface_consistency import build_surface_consistency

EXTRACTION_READINESS_VERSION = "1.0.0"

READINESS_CHECKS = [
    {
        "id": "package_inventory",
        "title": "Package inventory",
        "summary": "Required package, spec, docs, scripts, and root shim files are listed and present.",
        "proof": "Package manifest reports Complete: True.",
        "next_action": "Keep manifest updated before any standalone repository cut.",
    },
    {
        "id": "reviewer_artifacts",
        "title": "Reviewer artifacts",
        "summary": "Reviewer-facing generated artifacts are statically declared and discoverable.",
        "proof": "Review pack contract exposes the expected artifact file list.",
        "next_action": "Use review pack as the human extraction audit folder.",
    },
    {
        "id": "surface_consistency",
        "title": "Surface consistency",
        "summary": "Critical review surfaces are visible across catalog, snapshot, pack, and manifest.",
        "proof": "Surface consistency reports Complete: True.",
        "next_action": "Add any new extraction-critical surface to the consistency matrix.",
    },
    {
        "id": "known_gaps",
        "title": "Known gaps",
        "summary": "Blocking gaps are absent and planned policy boundaries remain explicit.",
        "proof": "Review gap register reports zero blocking gaps.",
        "next_action": "Do not hide future shell or adapter work as completed extraction scope.",
    },
    {
        "id": "closeout_handoff",
        "title": "Closeout handoff",
        "summary": "A maintainer can resume from the closeout pack and full gate without chat history.",
        "proof": "Closeout pack reports Complete: True.",
        "next_action": "Refresh closeout pack before extraction or release review.",
    },
]


def build_extraction_readiness(project_root: Path) -> dict[str, Any]:
    """Build a deterministic report for future standalone EACODE extraction."""

    root = resolve_project_root(project_root)
    package = build_package_manifest(root)
    surfaces = build_surface_consistency(root)
    gaps = build_review_gap_register(root)
    closeout = build_closeout_pack(root)
    review_pack_files = get_review_pack_artifact_files()

    blocking_gaps = [gap for gap in gaps["gaps"] if gap["blocking"]]
    checks = _build_checks(
        package_complete=package["complete"],
        surfaces_complete=surfaces["complete"],
        closeout_complete=closeout["complete"],
        review_pack_file_total=len(review_pack_files),
        blocking_gap_total=len(blocking_gaps),
    )
    incomplete_checks = [check["id"] for check in checks if not check["complete"]]

    return {
        "extraction_readiness_version": EXTRACTION_READINESS_VERSION,
        "project_root": str(root),
        "complete": not incomplete_checks,
        "check_total": len(checks),
        "complete_check_total": sum(1 for check in checks if check["complete"]),
        "incomplete_checks": incomplete_checks,
        "required_files": package["required_total"],
        "present_files": package["present_total"],
        "review_pack_files": len(review_pack_files),
        "surface_total": surfaces["surface_total"],
        "blocking_gaps": len(blocking_gaps),
        "checks": checks,
        "non_goals": [
            "Extraction readiness does not create a standalone repository.",
            "Extraction readiness does not copy files.",
            "Extraction readiness does not execute shell actions.",
            "Extraction readiness does not call LLM providers.",
            "Extraction readiness does not authorize shell, Aider, Cline, or OpenCode adapters.",
        ],
    }


def format_extraction_readiness_text(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Extraction Readiness",
            f"Version: {report['extraction_readiness_version']}",
            f"Complete: {report['complete']}",
            f"Checks: {report['complete_check_total']}/{report['check_total']}",
            f"Required files: {report['present_files']}/{report['required_files']}",
            f"Review pack files: {report['review_pack_files']}",
            f"Surfaces: {report['surface_total']}",
            f"Blocking gaps: {report['blocking_gaps']}",
            f"Incomplete checks: {_inline_list(report['incomplete_checks'])}",
        ]
    )


def format_extraction_readiness_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Energy Aware Code Extraction Readiness",
        "",
        f"- Version: {report['extraction_readiness_version']}",
        f"- Project root: {report['project_root']}",
        f"- Complete: {report['complete']}",
        f"- Checks: {report['complete_check_total']}/{report['check_total']}",
        f"- Required files: {report['present_files']}/{report['required_files']}",
        f"- Review pack files: {report['review_pack_files']}",
        f"- Surfaces: {report['surface_total']}",
        f"- Blocking gaps: {report['blocking_gaps']}",
        "",
        "## Incomplete checks",
        "",
    ]
    lines.extend(_bullet_list(report["incomplete_checks"]))
    lines.extend(["", "## Checks", ""])
    for check in report["checks"]:
        lines.extend(
            [
                f"### {check['title']}",
                "",
                f"- Id: {check['id']}",
                f"- Complete: {check['complete']}",
                f"- Summary: {check['summary']}",
                f"- Proof: {check['proof']}",
                f"- Next action: {check['next_action']}",
                "",
            ]
        )
    lines.extend(["## Non goals", ""])
    lines.extend(_bullet_list(report["non_goals"]))
    return "\n".join(lines)


def _build_checks(
    *,
    package_complete: bool,
    surfaces_complete: bool,
    closeout_complete: bool,
    review_pack_file_total: int,
    blocking_gap_total: int,
) -> list[dict[str, Any]]:
    status_by_id = {
        "package_inventory": package_complete,
        "reviewer_artifacts": review_pack_file_total >= 1,
        "surface_consistency": surfaces_complete,
        "known_gaps": blocking_gap_total == 0,
        "closeout_handoff": closeout_complete,
    }
    return [check | {"complete": status_by_id[check["id"]]} for check in READINESS_CHECKS]


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]
