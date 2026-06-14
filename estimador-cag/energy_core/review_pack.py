from __future__ import annotations

from pathlib import Path
from typing import Any

from energy_core.command_catalog import build_command_catalog, format_command_catalog_markdown
from energy_core.critic_coverage import (
    build_critic_coverage,
    format_critic_coverage_markdown,
)
from energy_core.export_plan import build_export_plan, format_export_plan_markdown
from energy_core.ledger_integrity import (
    build_ledger_integrity,
    format_ledger_integrity_markdown,
)
from energy_core.nightly_status import (
    build_nightly_status,
    format_nightly_status_markdown,
)
from energy_core.package_manifest import (
    build_package_manifest,
    format_package_manifest_markdown,
    resolve_project_root,
)
from energy_core.release import build_release_readiness, format_release_readiness_markdown
from energy_core.reviewer_index import (
    build_reviewer_snapshot,
    format_reviewer_snapshot_markdown,
)

REVIEW_PACK_VERSION = "1.0.0"
DEFAULT_SPEC_DIR = Path(".energy/specs/0001-energy-policy-ledger")
DEFAULT_POLICY = DEFAULT_SPEC_DIR / "energy-policy.yaml"
DEFAULT_CANDIDATE = DEFAULT_SPEC_DIR / "examples/candidate_accept.json"
DEFAULT_EVIDENCE = DEFAULT_SPEC_DIR / "evidence.jsonl"
DEFAULT_LEDGER = DEFAULT_SPEC_DIR / "decisions.jsonl"


def build_review_pack(project_root: Path, output_dir: Path) -> dict[str, Any]:
    """Write a deterministic reviewer artifact pack to an output directory."""

    root = resolve_project_root(project_root)
    destination = output_dir.resolve()
    destination.mkdir(parents=True, exist_ok=True)

    artifacts = _render_artifacts(root)
    files: list[dict[str, Any]] = []

    for filename, content in artifacts.items():
        path = destination / filename
        path.write_text(content, encoding="utf-8")
        files.append(
            {
                "filename": filename,
                "path": str(path),
                "exists": path.is_file(),
                "size_bytes": path.stat().st_size if path.exists() else 0,
            }
        )

    missing = [item["filename"] for item in files if not item["exists"]]

    return {
        "review_pack_version": REVIEW_PACK_VERSION,
        "project_root": str(root),
        "output_dir": str(destination),
        "complete": not missing,
        "file_total": len(files),
        "present_total": len(files) - len(missing),
        "missing": missing,
        "files": files,
        "non_goals": [
            "Review pack export does not execute shell actions.",
            "Review pack export does not call LLM providers.",
            "Review pack export does not approve adapter execution.",
            "Review pack export does not append to the decision ledger.",
        ],
    }


def format_review_pack_text(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Review Pack",
            f"Version: {summary['review_pack_version']}",
            f"Project root: {summary['project_root']}",
            f"Output dir: {summary['output_dir']}",
            f"Complete: {summary['complete']}",
            f"Files: {summary['present_total']}/{summary['file_total']}",
            f"Missing: {_inline_list(summary['missing'])}",
        ]
    )


def format_review_pack_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Energy Aware Code Review Pack",
        "",
        f"- Version: {summary['review_pack_version']}",
        f"- Project root: {summary['project_root']}",
        f"- Output dir: {summary['output_dir']}",
        f"- Complete: {summary['complete']}",
        f"- Files: {summary['present_total']}/{summary['file_total']}",
        "",
        "## Missing",
        "",
    ]
    lines.extend(_bullet_list(summary["missing"]))
    lines.extend(["", "## Files", ""])
    for item in summary["files"]:
        status = "present" if item["exists"] else "missing"
        lines.append(f"- {item['filename']} ({status}, size={item['size_bytes']} bytes)")
    lines.extend(["", "## Non goals", ""])
    lines.extend(_bullet_list(summary["non_goals"]))
    return "\n".join(lines)


def _render_artifacts(project_root: Path) -> dict[str, str]:
    reviewer = build_reviewer_snapshot(project_root)
    package = build_package_manifest(project_root)
    command_catalog = build_command_catalog()
    export_plan = build_export_plan(project_root)
    nightly_status = build_nightly_status(project_root)
    critic_coverage = build_critic_coverage(project_root / DEFAULT_POLICY)
    ledger_integrity = build_ledger_integrity(project_root / DEFAULT_LEDGER)
    release = build_release_readiness(
        project_root=project_root,
        spec_dir=project_root / DEFAULT_SPEC_DIR,
        policy_path=project_root / DEFAULT_POLICY,
        candidate_path=project_root / DEFAULT_CANDIDATE,
        evidence_path=project_root / DEFAULT_EVIDENCE,
        decisions_path=None,
    )

    index = "\n".join(
        [
            "# EACODE Review Pack",
            "",
            "Generated deterministic review artifacts:",
            "",
            "- reviewer_snapshot.md",
            "- nightly_status.md",
            "- release_readiness.md",
            "- package_manifest.md",
            "- export_plan.md",
            "- command_catalog.md",
            "- critic_coverage.md",
            "- ledger_integrity.md",
            "",
            "This pack is generated from repository files and does not execute",
            "adapters, shell actions, or provider calls.",
            "",
        ]
    )

    return {
        "README.md": index,
        "reviewer_snapshot.md": format_reviewer_snapshot_markdown(reviewer),
        "nightly_status.md": format_nightly_status_markdown(nightly_status),
        "release_readiness.md": format_release_readiness_markdown(release),
        "package_manifest.md": format_package_manifest_markdown(package),
        "export_plan.md": format_export_plan_markdown(export_plan),
        "command_catalog.md": format_command_catalog_markdown(command_catalog),
        "critic_coverage.md": format_critic_coverage_markdown(critic_coverage),
        "ledger_integrity.md": format_ledger_integrity_markdown(ledger_integrity),
    }


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]
