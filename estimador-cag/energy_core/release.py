from __future__ import annotations

from pathlib import Path
from typing import Any

from energy_core.audit import build_audit_pack

FORBIDDEN_BOUNDARY_TOKENS = {
    "from app",
    "import app",
    "fastapi",
    "streamlit",
    "litellm",
    "openai",
    "anthropic",
    "redis",
    "cline",
    "aider",
    "opencode",
}

REQUIRED_RELEASE_DOCS = [
    "docs/energy_aware_code_usage.md",
    "docs/energy_aware_code_extraction_plan.md",
    "docs/energy_aware_code_roadmap.md",
]

REQUIRED_RELEASE_SCRIPTS = [
    "scripts/energy_core_smoke.py",
]


def build_release_readiness(
    *,
    project_root: Path,
    spec_dir: Path,
    policy_path: Path,
    candidate_path: Path,
    evidence_path: Path,
    decisions_path: Path | None = None,
) -> dict[str, Any]:
    """Build a deterministic readiness packet for eventual repository extraction."""

    project_root = project_root.resolve()
    audit_pack = build_audit_pack(
        spec_dir=spec_dir,
        policy_path=policy_path,
        candidate_path=candidate_path,
        evidence_path=evidence_path,
        decisions_path=decisions_path,
    )
    boundary = scan_energy_core_boundary(project_root)
    artifacts = summarize_release_artifacts(project_root)
    supplied_decisions_missing = decisions_path is not None and not decisions_path.exists()

    blockers: list[str] = []
    if not audit_pack["ready_to_accept"]:
        blockers.append("audit_pack_not_ready")
    if not boundary["clean"]:
        blockers.append("package_boundary_violation")
    if not artifacts["complete"]:
        blockers.append("release_artifacts_missing")
    if supplied_decisions_missing:
        blockers.append("supplied_decisions_missing")

    ready = not blockers

    return {
        "complete": ready,
        "ready_to_extract": ready,
        "project_root": str(project_root),
        "blockers": blockers,
        "audit_pack": audit_pack,
        "boundary": boundary,
        "release_artifacts": artifacts,
        "supplied_decisions_missing": supplied_decisions_missing,
    }


def scan_energy_core_boundary(project_root: Path) -> dict[str, Any]:
    """Scan energy_core source for forbidden product-layer imports."""

    package_root = project_root / "energy_core"
    violations: list[dict[str, str]] = []

    for path in sorted(package_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8").lower()
        for token in sorted(FORBIDDEN_BOUNDARY_TOKENS):
            if token in text:
                violations.append(
                    {
                        "path": str(path),
                        "token": token,
                    }
                )

    return {
        "clean": not violations,
        "package_root": str(package_root),
        "violations": violations,
        "checked_files": len(list(package_root.rglob("*.py"))),
    }


def summarize_release_artifacts(project_root: Path) -> dict[str, Any]:
    """Check release-facing docs and smoke scripts that make extraction practical."""

    required = [*REQUIRED_RELEASE_DOCS, *REQUIRED_RELEASE_SCRIPTS]
    files = []
    missing: list[str] = []

    for relative_path in required:
        path = project_root / relative_path
        exists = path.is_file()
        if not exists:
            missing.append(relative_path)
        files.append(
            {
                "path": relative_path,
                "exists": exists,
            }
        )

    return {
        "complete": not missing,
        "required_total": len(required),
        "present_total": sum(1 for item in files if item["exists"]),
        "missing": missing,
        "files": files,
    }


def format_release_readiness_markdown(summary: dict[str, Any]) -> str:
    """Render release readiness as Markdown for a human handoff."""

    audit = summary["audit_pack"]
    boundary = summary["boundary"]
    artifacts = summary["release_artifacts"]

    return "\n".join(
        [
            "# Energy Aware Code Release Readiness",
            "",
            f"- Ready to extract: {summary['ready_to_extract']}",
            f"- Project root: {summary['project_root']}",
            f"- Blockers: {_inline_list(summary['blockers'])}",
            "",
            "## Audit pack",
            "",
            f"- Ready to accept: {audit['ready_to_accept']}",
            f"- Decision preview: {audit['decision']['decision']}",
            f"- Energy after: {audit['decision']['energy_after']}",
            f"- Bundle complete: {audit['bundle_manifest']['complete']}",
            "",
            "## Package boundary",
            "",
            f"- Clean: {boundary['clean']}",
            f"- Checked files: {boundary['checked_files']}",
            f"- Violations: {_format_boundary_violations(boundary['violations'])}",
            "",
            "## Release artifacts",
            "",
            f"- Complete: {artifacts['complete']}",
            f"- Present: {artifacts['present_total']}/{artifacts['required_total']}",
            f"- Missing: {_inline_list(artifacts['missing'])}",
            "",
        ]
    )


def format_release_readiness_text(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Release Readiness",
            f"Ready to extract: {summary['ready_to_extract']}",
            f"Project root: {summary['project_root']}",
            f"Blockers: {_inline_list(summary['blockers'])}",
            f"Boundary clean: {summary['boundary']['clean']}",
            f"Release artifacts complete: {summary['release_artifacts']['complete']}",
        ]
    )


def _format_boundary_violations(violations: list[dict[str, str]]) -> str:
    if not violations:
        return "none"
    return ", ".join(f"{item['path']}:{item['token']}" for item in violations)


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"
