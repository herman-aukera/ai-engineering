from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

MANIFEST_VERSION = "1.0.0"

REQUIRED_PACKAGE_FILES = [
    "energy_core/__init__.py",
    "energy_core/adapter_contracts.py",
    "energy_core/audit.py",
    "energy_core/bundle.py",
    "energy_core/cli.py",
    "energy_core/command_catalog.py",
    "energy_core/command_catalog_cli.py",
    "energy_core/constraints.py",
    "energy_core/constraints_cli.py",
    "energy_core/critic_coverage.py",
    "energy_core/critic_coverage_cli.py",
    "energy_core/critics.py",
    "energy_core/decider.py",
    "energy_core/evidence.py",
    "energy_core/examples.py",
    "energy_core/examples_cli.py",
    "energy_core/export_plan.py",
    "energy_core/export_plan_cli.py",
    "energy_core/ledger.py",
    "energy_core/ledger_integrity.py",
    "energy_core/ledger_integrity_cli.py",
    "energy_core/models.py",
    "energy_core/package_cli.py",
    "energy_core/package_manifest.py",
    "energy_core/policy.py",
    "energy_core/release.py",
    "energy_core/release_cli.py",
    "energy_core/reporter.py",
    "energy_core/review_pack.py",
    "energy_core/review_pack_cli.py",
    "energy_core/reviewer_cli.py",
    "energy_core/reviewer_index.py",
    "energy_core/schema_bundle.py",
    "energy_core/schema_cli.py",
    "energy_core/scaffold.py",
    "energy_core/scaffold_cli.py",
    "energy_core/scorer.py",
    "energy_core/specs.py",
    "energy_core/state.py",
    "energy_core/trends.py",
    "energy_core/validation.py",
    "energy_core/validation_reporter.py",
]

REQUIRED_SPEC_FILES = [
    ".energy/specs/0001-energy-policy-ledger/requirements.md",
    ".energy/specs/0001-energy-policy-ledger/design.md",
    ".energy/specs/0001-energy-policy-ledger/tasks.md",
    ".energy/specs/0001-energy-policy-ledger/acceptance.md",
    ".energy/specs/0001-energy-policy-ledger/energy-policy.yaml",
    ".energy/specs/0001-energy-policy-ledger/evidence.jsonl",
    ".energy/specs/0001-energy-policy-ledger/examples/candidate_accept.json",
    ".energy/specs/0001-energy-policy-ledger/examples/candidate_repair_missing_evidence.json",
    ".energy/specs/0001-energy-policy-ledger/examples/candidate_reject_tests_failed.json",
    ".energy/specs/0001-energy-policy-ledger/examples/candidate_reject_scope_creep.json",
]

REQUIRED_DOC_FILES = [
    "docs/energy_aware_code_usage.md",
    "docs/energy_aware_code_extraction_plan.md",
    "docs/energy_aware_code_roadmap.md",
    "docs/energy_aware_code_package_manifest.md",
    "docs/energy_aware_code_reviewer_snapshot.md",
    "docs/energy_aware_code_command_catalog.md",
    "docs/energy_aware_code_review_pack.md",
    "docs/energy_aware_code_critic_coverage.md",
    "docs/energy_aware_code_ledger_integrity.md",
]

REQUIRED_SCRIPT_FILES = [
    "scripts/energy_core_boundary_check.py",
    "scripts/energy_core_smoke.py",
    "scripts/energy_core_example_smoke.py",
    "scripts/energy_core_constraint_smoke.py",
    "scripts/energy_core_release_smoke.py",
    "scripts/energy_core_package_smoke.py",
    "scripts/energy_core_reviewer_smoke.py",
    "scripts/energy_core_command_catalog_smoke.py",
    "scripts/energy_core_review_pack_smoke.py",
    "scripts/energy_core_critic_coverage_smoke.py",
    "scripts/energy_core_ledger_integrity_smoke.py",
    "scripts/energy_core_schema_smoke.py",
    "scripts/energy_core_scaffold_smoke.py",
    "scripts/energy_core_export_plan_smoke.py",
    "scripts/energy_core_full_gate.py",
]

INCUBATOR_ROOT_FILES = [
    "../energy_core/__init__.py",
]


def resolve_project_root(project_root: Path) -> Path:
    """Resolve either estimador-cag or repository root to the project root."""

    root = project_root.resolve()
    if (root / "energy_core").is_dir() and (root / ".energy").is_dir():
        return root
    nested = root / "estimador-cag"
    if (nested / "energy_core").is_dir() and (nested / ".energy").is_dir():
        return nested.resolve()
    return root


def build_package_manifest(project_root: Path) -> dict[str, Any]:
    """Build a deterministic manifest for future standalone repository extraction."""

    root = resolve_project_root(project_root)
    required_groups = {
        "package": REQUIRED_PACKAGE_FILES,
        "spec": REQUIRED_SPEC_FILES,
        "docs": REQUIRED_DOC_FILES,
        "scripts": REQUIRED_SCRIPT_FILES,
        "incubator_root": INCUBATOR_ROOT_FILES,
    }

    files: list[dict[str, Any]] = []
    missing_required: list[str] = []

    for group, paths in required_groups.items():
        for relative_path in paths:
            record = _file_record(root, group, relative_path)
            files.append(record)
            if not record["exists"]:
                missing_required.append(relative_path)

    return {
        "manifest_version": MANIFEST_VERSION,
        "project_root": str(root),
        "complete": not missing_required,
        "required_total": len(files),
        "present_total": sum(1 for item in files if item["exists"]),
        "missing_required": missing_required,
        "files": files,
        "copy_roots": [
            "energy_core/",
            ".energy/",
            "docs/energy_aware_code_*.md",
            "scripts/energy_core_*.py",
        ],
        "non_goals": [
            "No shell execution is included in the package manifest.",
            "No provider keys or model clients are included in the package manifest.",
            "No Aider, Cline, or OpenCode adapter code is included.",
        ],
    }


def format_package_manifest_text(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Package Manifest",
            f"Manifest version: {manifest['manifest_version']}",
            f"Project root: {manifest['project_root']}",
            f"Complete: {manifest['complete']}",
            f"Present files: {manifest['present_total']}/{manifest['required_total']}",
            f"Missing required: {_inline_list(manifest['missing_required'])}",
        ]
    )


def format_package_manifest_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# Energy Aware Code Package Manifest",
        "",
        f"- Manifest version: {manifest['manifest_version']}",
        f"- Project root: {manifest['project_root']}",
        f"- Complete: {manifest['complete']}",
        f"- Present files: {manifest['present_total']}/{manifest['required_total']}",
        "",
        "## Missing required",
        "",
    ]
    lines.extend(_bullet_list(manifest["missing_required"]))
    lines.extend(["", "## Copy roots", ""])
    lines.extend(_bullet_list(manifest["copy_roots"]))
    lines.extend(["", "## Files", ""])
    for item in manifest["files"]:
        status = "present" if item["exists"] else "missing"
        summary = f"{status}, sha256={item['sha256'] or 'none'}"
        lines.append(f"- {item['group']}: {item['relative_path']} ({summary})")
    lines.extend(["", "## Non goals", ""])
    lines.extend(_bullet_list(manifest["non_goals"]))
    return "\n".join(lines)


def _file_record(project_root: Path, group: str, relative_path: str) -> dict[str, Any]:
    path = (project_root / relative_path).resolve()
    exists = path.is_file()
    return {
        "group": group,
        "relative_path": relative_path,
        "path": str(path),
        "exists": exists,
        "size_bytes": path.stat().st_size if exists else None,
        "sha256": _sha256(path) if exists else None,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]
