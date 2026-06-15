from __future__ import annotations

from pathlib import Path
from typing import Any

from energy_core.package_manifest import build_package_manifest, resolve_project_root
from energy_core.review_gap_register import build_review_gap_register
from energy_core.surface_consistency import build_surface_consistency

DEMO_WALKTHROUGH_VERSION = "1.0.0"

DEMO_STEPS = [
    {
        "id": "review_pack",
        "title": "Open the generated review pack",
        "command": "python -m energy_core.review_pack_cli --format markdown --fail-on-incomplete",
        "proof": "Review pack reports Complete: True and writes reviewer artifacts.",
        "talk_track": "Start with one folder instead of many scattered command outputs.",
    },
    {
        "id": "surface_consistency",
        "title": "Show surface consistency",
        "command": "python -m energy_core.surface_consistency_cli --format markdown",
        "proof": "Surface consistency reports Complete: True and no missing surfaces.",
        "talk_track": "Prove that review surfaces are visible across catalog, snapshot, pack, and manifest.",
    },
    {
        "id": "acceptance_trace",
        "title": "Show acceptance trace",
        "command": "python -m energy_core.acceptance_trace_cli --format markdown --fail-on-incomplete",
        "proof": "Acceptance trace reports all criteria traced to evidence and tests.",
        "talk_track": "Connect the original acceptance criteria to concrete tests and evidence.",
    },
    {
        "id": "review_gap_register",
        "title": "Show known gaps",
        "command": "python -m energy_core.review_gap_register_cli --format markdown --fail-on-blocking",
        "proof": "Review gap register reports zero blocking gaps and explicit planned boundaries.",
        "talk_track": "Show what is still intentionally not built instead of hiding limitations.",
    },
    {
        "id": "full_gate",
        "title": "Run the one-command full gate",
        "command": "python scripts/energy_core_full_gate.py --fix",
        "proof": "Full gate runs Ruff, compile, tests, smoke scripts, root smoke, and git cleanliness.",
        "talk_track": "End with the same validator used by CI and local development.",
    },
]


def build_demo_walkthrough(project_root: Path) -> dict[str, Any]:
    """Build a reviewer-facing demo walkthrough without executing commands."""

    root = resolve_project_root(project_root)
    package = build_package_manifest(root)
    surfaces = build_surface_consistency(root)
    gaps = build_review_gap_register(root)

    missing_step_surfaces = [
        step["id"]
        for step in DEMO_STEPS
        if step["id"] not in {"review_pack", "full_gate"}
        and step["id"] not in {row["surface_id"] for row in surfaces["rows"]}
    ]
    blocking_gaps = [gap for gap in gaps["gaps"] if gap["blocking"]]

    complete = package["complete"] and surfaces["complete"] and not missing_step_surfaces and not blocking_gaps

    return {
        "demo_walkthrough_version": DEMO_WALKTHROUGH_VERSION,
        "project_root": str(root),
        "complete": complete,
        "step_total": len(DEMO_STEPS),
        "missing_step_surfaces": missing_step_surfaces,
        "blocking_gap_total": len(blocking_gaps),
        "package_manifest_complete": package["complete"],
        "surface_consistency_complete": surfaces["complete"],
        "steps": DEMO_STEPS,
        "non_goals": [
            "Demo walkthrough does not execute shell actions.",
            "Demo walkthrough does not call LLM providers.",
            "Demo walkthrough does not mutate evidence or the decision ledger.",
            "Demo walkthrough is a human demo script, not a benchmark result.",
        ],
    }


def format_demo_walkthrough_text(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Demo Walkthrough",
            f"Version: {report['demo_walkthrough_version']}",
            f"Complete: {report['complete']}",
            f"Steps: {report['step_total']}",
            f"Missing step surfaces: {_inline_list(report['missing_step_surfaces'])}",
            f"Blocking gaps: {report['blocking_gap_total']}",
        ]
    )


def format_demo_walkthrough_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Energy Aware Code Demo Walkthrough",
        "",
        f"- Version: {report['demo_walkthrough_version']}",
        f"- Project root: {report['project_root']}",
        f"- Complete: {report['complete']}",
        f"- Steps: {report['step_total']}",
        f"- Package manifest complete: {report['package_manifest_complete']}",
        f"- Surface consistency complete: {report['surface_consistency_complete']}",
        f"- Blocking gaps: {report['blocking_gap_total']}",
        "",
        "## Missing step surfaces",
        "",
    ]
    lines.extend(_bullet_list(report["missing_step_surfaces"]))
    lines.extend(["", "## Demo sequence", ""])
    for index, step in enumerate(report["steps"], start=1):
        lines.extend(
            [
                f"### Step {index}: {step['title']}",
                "",
                f"- Id: {step['id']}",
                f"- Command: `{step['command']}`",
                f"- Proof: {step['proof']}",
                f"- Talk track: {step['talk_track']}",
                "",
            ]
        )
    lines.extend(["## Non goals", ""])
    lines.extend(_bullet_list(report["non_goals"]))
    return "\n".join(lines)


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]
