from __future__ import annotations

from pathlib import Path
from typing import Any

from energy_core.acceptance_trace import build_acceptance_trace
from energy_core.course_boundary import build_course_boundary_report
from energy_core.demo_walkthrough import build_demo_walkthrough
from energy_core.package_manifest import build_package_manifest, resolve_project_root
from energy_core.review_gap_register import build_review_gap_register
from energy_core.review_pack_contract import get_review_pack_artifact_files
from energy_core.surface_consistency import build_surface_consistency

CLOSEOUT_PACK_VERSION = "1.0.0"

CLOSEOUT_SECTIONS = [
    {
        "id": "incubator_status",
        "title": "Incubator status",
        "summary": "EACODE remains a draft, judge-layer incubator with explicit course boundaries.",
        "proof": "course_boundary reports Complete: True and zero blocking conflicts.",
        "next_action": "Keep PR #4 draft until an explicit release or extraction decision exists.",
    },
    {
        "id": "reviewer_evidence_index",
        "title": "Reviewer evidence index",
        "summary": "Review pack, surface consistency, and package manifest expose the current proof surfaces.",
        "proof": "review pack artifacts are statically registered and surface consistency is complete.",
        "next_action": "Use the generated review pack as the first reviewer artifact.",
    },
    {
        "id": "acceptance_evidence_trace",
        "title": "Acceptance evidence trace",
        "summary": "Acceptance criteria are connected to tests, evidence types, and reviewer surfaces.",
        "proof": "acceptance_trace reports Complete: True and no missing required acceptance evidence.",
        "next_action": "Refresh the trace whenever acceptance criteria or evidence contracts change.",
    },
    {
        "id": "day_end_handoff",
        "title": "Day-end handoff checklist",
        "summary": "A maintainer can resume from review pack, demo walkthrough, gap register, and full gate.",
        "proof": "demo_walkthrough reports Complete: True and review_gap_register has zero blocking gaps.",
        "next_action": "Start the next session by pulling EACODE and running the full gate.",
    },
    {
        "id": "next_slice_roadmap",
        "title": "Next-slice roadmap",
        "summary": "Future work stays bounded to judge-layer hardening until shell evidence is explicitly approved.",
        "proof": "review_gap_register lists planned policy boundaries instead of hiding them.",
        "next_action": "Choose one next slice: PR refresh, policy evolution, or controlled shell evidence design only.",
    },
]


def build_closeout_pack(project_root: Path) -> dict[str, Any]:
    """Build an end-of-day closeout report without executing commands."""

    root = resolve_project_root(project_root)
    package = build_package_manifest(root)
    surfaces = build_surface_consistency(root)
    gaps = build_review_gap_register(root)
    acceptance = build_acceptance_trace(root)
    boundary = build_course_boundary_report(root)
    demo = build_demo_walkthrough(root)
    review_pack_files = get_review_pack_artifact_files()

    blocking_gaps = [gap for gap in gaps["gaps"] if gap["blocking"]]
    missing_required_evidence = acceptance["missing_required_acceptance"]
    blocking_conflicts = boundary["blocking_conflicts"]

    section_status = _build_section_status(
        package_complete=package["complete"],
        surfaces_complete=surfaces["complete"],
        acceptance_complete=acceptance["complete"],
        demo_complete=demo["complete"],
        blocking_gap_total=len(blocking_gaps),
        blocking_conflict_total=len(blocking_conflicts),
        review_pack_file_total=len(review_pack_files),
        missing_required_evidence=missing_required_evidence,
    )

    incomplete_sections = [section["id"] for section in section_status if not section["complete"]]

    return {
        "closeout_pack_version": CLOSEOUT_PACK_VERSION,
        "project_root": str(root),
        "complete": not incomplete_sections,
        "section_total": len(section_status),
        "complete_section_total": sum(1 for section in section_status if section["complete"]),
        "incomplete_sections": incomplete_sections,
        "review_pack_file_total": len(review_pack_files),
        "surface_total": surfaces["surface_total"],
        "blocking_gap_total": len(blocking_gaps),
        "blocking_conflict_total": len(blocking_conflicts),
        "missing_required_acceptance_evidence": missing_required_evidence,
        "sections": section_status,
        "non_goals": [
            "Closeout pack does not execute shell actions.",
            "Closeout pack does not call LLM providers.",
            "Closeout pack does not mutate evidence or the decision ledger.",
            "Closeout pack does not authorize shell, Aider, Cline, or OpenCode adapters.",
            "Closeout pack is a planning and handoff artifact, not a benchmark result.",
        ],
    }


def format_closeout_pack_text(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Closeout Pack",
            f"Version: {report['closeout_pack_version']}",
            f"Complete: {report['complete']}",
            f"Sections: {report['complete_section_total']}/{report['section_total']}",
            f"Review pack files: {report['review_pack_file_total']}",
            f"Surfaces: {report['surface_total']}",
            f"Blocking gaps: {report['blocking_gap_total']}",
            f"Incomplete sections: {_inline_list(report['incomplete_sections'])}",
        ]
    )


def format_closeout_pack_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Energy Aware Code Closeout Pack",
        "",
        f"- Version: {report['closeout_pack_version']}",
        f"- Project root: {report['project_root']}",
        f"- Complete: {report['complete']}",
        f"- Sections: {report['complete_section_total']}/{report['section_total']}",
        f"- Review pack files: {report['review_pack_file_total']}",
        f"- Surfaces: {report['surface_total']}",
        f"- Blocking gaps: {report['blocking_gap_total']}",
        f"- Blocking course conflicts: {report['blocking_conflict_total']}",
        "",
        "## Incomplete sections",
        "",
    ]
    lines.extend(_bullet_list(report["incomplete_sections"]))
    lines.extend(["", "## Missing required acceptance evidence", ""])
    lines.extend(_bullet_list(report["missing_required_acceptance_evidence"]))
    lines.extend(["", "## Closeout sections", ""])
    for section in report["sections"]:
        lines.extend(
            [
                f"### {section['title']}",
                "",
                f"- Id: {section['id']}",
                f"- Complete: {section['complete']}",
                f"- Summary: {section['summary']}",
                f"- Proof: {section['proof']}",
                f"- Next action: {section['next_action']}",
                "",
            ]
        )
    lines.extend(["## Non goals", ""])
    lines.extend(_bullet_list(report["non_goals"]))
    return "\n".join(lines)


def _build_section_status(
    *,
    package_complete: bool,
    surfaces_complete: bool,
    acceptance_complete: bool,
    demo_complete: bool,
    blocking_gap_total: int,
    blocking_conflict_total: int,
    review_pack_file_total: int,
    missing_required_evidence: list[str],
) -> list[dict[str, Any]]:
    status_by_id = {
        "incubator_status": package_complete and blocking_conflict_total == 0,
        "reviewer_evidence_index": package_complete and surfaces_complete and review_pack_file_total >= 1,
        "acceptance_evidence_trace": acceptance_complete and not missing_required_evidence,
        "day_end_handoff": demo_complete and blocking_gap_total == 0,
        "next_slice_roadmap": blocking_conflict_total == 0,
    }

    return [section | {"complete": status_by_id[section["id"]]} for section in CLOSEOUT_SECTIONS]


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]
