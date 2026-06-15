from __future__ import annotations

from pathlib import Path
from typing import Any

from energy_core.package_manifest import resolve_project_root

COURSE_BOUNDARY_VERSION = "1.0.0"

_BOUNDARIES = [
    {
        "id": "eacode_incubator",
        "scope": "Energy Aware Code",
        "status": "active",
        "summary": "EACODE is a long-lived product incubator branch.",
        "rule": "Do not treat EACODE as a normal Session 08, Session 09, or mainline coursework branch.",
    },
    {
        "id": "session08_pgvector",
        "scope": "Session 08 coursework",
        "status": "separate_branch_required",
        "summary": "Session 08 pgvector/search work belongs on its own coursework branch.",
        "rule": "Do not backfill Session 08 database work into EACODE unless the change is product documentation only.",
    },
    {
        "id": "session09_evaluation_quality",
        "scope": "Session 09 coursework",
        "status": "separate_branch_required",
        "summary": "Session 09 evaluation-quality work belongs on its own coursework branch.",
        "rule": "Do not mix Task 09 evaluation implementation with EACODE judge-layer incubation.",
    },
    {
        "id": "eachat_boundary",
        "scope": "Energy Aware Chat",
        "status": "separate_product",
        "summary": "EACHAT is the sibling product and must remain independently useful.",
        "rule": "Do not merge Chat implementation into EACODE unless the slice is documentation-only bridge alignment.",
    },
    {
        "id": "finalproject_boundary",
        "scope": "Final project delivery",
        "status": "future_cut",
        "summary": "The final project branch should be cut later from the strongest stable candidate.",
        "rule": "Do not rename EACODE into the final delivery branch until the final candidate is selected.",
    },
]

_NEXT_ACTIONS = [
    "Keep EACODE as an open draft incubator PR.",
    "Use separate coursework branches for Session 08 and Session 09 deliverables.",
    "Use review pack and full gate before presenting EACODE to a reviewer.",
    "Cut a finalproject branch only when the final delivery candidate is stable.",
]

_NON_GOALS = [
    "Course boundary report does not execute shell actions.",
    "Course boundary report does not inspect live git state.",
    "Course boundary report does not call LLM providers.",
    "Course boundary report does not mutate evidence or the decision ledger.",
]


def build_course_boundary_report(project_root: Path) -> dict[str, Any]:
    """Build a static boundary report for EACODE versus coursework branches."""

    root = resolve_project_root(project_root)
    return {
        "version": COURSE_BOUNDARY_VERSION,
        "project_root": str(root),
        "complete": True,
        "active_product": "EACODE",
        "branch_role": "long-lived incubator",
        "boundaries_total": len(_BOUNDARIES),
        "blocking_conflicts": [],
        "boundaries": list(_BOUNDARIES),
        "next_actions": list(_NEXT_ACTIONS),
        "non_goals": list(_NON_GOALS),
    }


def format_course_boundary_text(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Course Boundary",
            f"Version: {report['version']}",
            f"Project root: {report['project_root']}",
            f"Complete: {report['complete']}",
            f"Active product: {report['active_product']}",
            f"Branch role: {report['branch_role']}",
            f"Boundaries: {report['boundaries_total']}",
            f"Blocking conflicts: {_inline_list(report['blocking_conflicts'])}",
        ]
    )


def format_course_boundary_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Energy Aware Code Course Boundary",
        "",
        f"- Version: {report['version']}",
        f"- Project root: {report['project_root']}",
        f"- Complete: {report['complete']}",
        f"- Active product: {report['active_product']}",
        f"- Branch role: {report['branch_role']}",
        f"- Boundaries: {report['boundaries_total']}",
        "",
        "## Blocking conflicts",
        "",
    ]
    lines.extend(_bullet_list(report["blocking_conflicts"]))
    lines.extend(["", "## Boundaries", ""])
    for item in report["boundaries"]:
        lines.extend(
            [
                f"### {item['id']}",
                "",
                f"- Scope: {item['scope']}",
                f"- Status: {item['status']}",
                f"- Summary: {item['summary']}",
                f"- Rule: {item['rule']}",
                "",
            ]
        )
    lines.extend(["## Next actions", ""])
    lines.extend(_bullet_list(report["next_actions"]))
    lines.extend(["", "## Non goals", ""])
    lines.extend(_bullet_list(report["non_goals"]))
    return "\n".join(lines)


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items if item] or ["- none"]
