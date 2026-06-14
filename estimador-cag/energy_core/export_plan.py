from __future__ import annotations

from pathlib import Path
from typing import Any

from energy_core.package_manifest import build_package_manifest

EXPORT_PLAN_VERSION = "1.0.0"

COPYABLE_GROUPS = {"package", "spec", "docs", "scripts"}
EXCLUDED_GROUPS = {"incubator_root"}


def build_export_plan(project_root: Path) -> dict[str, Any]:
    """Build a deterministic plan for future standalone repository extraction.

    The plan is intentionally non-executing. It reports what should be copied,
    what remains excluded, and what validation steps the future repository must
    pass after manual or tool-assisted extraction.
    """

    manifest = build_package_manifest(project_root)
    copy_items = [
        {
            "group": item["group"],
            "source_relative_path": item["relative_path"],
            "exists": item["exists"],
            "sha256": item["sha256"],
        }
        for item in manifest["files"]
        if item["group"] in COPYABLE_GROUPS
    ]
    excluded_items = [
        {
            "group": item["group"],
            "source_relative_path": item["relative_path"],
            "reason": "Course-repo root shim; not needed in a standalone package.",
        }
        for item in manifest["files"]
        if item["group"] in EXCLUDED_GROUPS
    ]
    missing_copy_items = [
        item["source_relative_path"] for item in copy_items if not item["exists"]
    ]

    return {
        "plan_version": EXPORT_PLAN_VERSION,
        "project_root": manifest["project_root"],
        "ready": manifest["complete"] and not missing_copy_items,
        "package_manifest_complete": manifest["complete"],
        "copy_item_total": len(copy_items),
        "copy_item_present": sum(1 for item in copy_items if item["exists"]),
        "missing_copy_items": missing_copy_items,
        "copy_items": copy_items,
        "excluded_items": excluded_items,
        "steps": [
            "Generate standalone scaffold with energy_core.scaffold_cli.",
            "Copy the listed package, spec, docs, and script files into the new repository.",
            "Do not copy course-only root shims unless a monorepo compatibility layer is still needed.",
            "Run the standalone repository validation commands from docs/VALIDATION_COMMANDS.md.",
            "Run package manifest and release readiness again after copying.",
        ],
        "non_goals": [
            "Export plan does not copy files automatically.",
            "Export plan does not create or push a repository.",
            "Export plan does not execute shell actions.",
            "Export plan does not call LLM providers.",
        ],
    }


def format_export_plan_text(plan: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Export Plan",
            f"Version: {plan['plan_version']}",
            f"Project root: {plan['project_root']}",
            f"Ready: {plan['ready']}",
            f"Copy items: {plan['copy_item_present']}/{plan['copy_item_total']}",
            f"Missing: {_inline_list(plan['missing_copy_items'])}",
        ]
    )


def format_export_plan_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Energy Aware Code Export Plan",
        "",
        f"- Version: {plan['plan_version']}",
        f"- Project root: {plan['project_root']}",
        f"- Ready: {plan['ready']}",
        f"- Package manifest complete: {plan['package_manifest_complete']}",
        f"- Copy items: {plan['copy_item_present']}/{plan['copy_item_total']}",
        "",
        "## Missing copy items",
        "",
    ]
    lines.extend(_bullet_list(plan["missing_copy_items"]))
    lines.extend(["", "## Copy items", ""])
    for item in plan["copy_items"]:
        status = "present" if item["exists"] else "missing"
        lines.append(
            f"- {item['group']}: {item['source_relative_path']} ({status}, sha256={item['sha256'] or 'none'})"
        )
    lines.extend(["", "## Excluded items", ""])
    if plan["excluded_items"]:
        for item in plan["excluded_items"]:
            lines.append(
                f"- {item['group']}: {item['source_relative_path']} ({item['reason']})"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Steps", ""])
    lines.extend(f"{index}. {step}" for index, step in enumerate(plan["steps"], start=1))
    lines.extend(["", "## Non goals", ""])
    lines.extend(_bullet_list(plan["non_goals"]))
    return "\n".join(lines)


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]
