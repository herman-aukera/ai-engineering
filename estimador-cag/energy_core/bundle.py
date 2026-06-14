from __future__ import annotations

import hashlib
from pathlib import Path

from energy_core.specs import OPTIONAL_SPEC_FILES, REQUIRED_EXAMPLE_FILES, REQUIRED_SPEC_FILES


def build_bundle_manifest(
    *,
    spec_dir: Path,
    policy_path: Path,
    candidate_path: Path,
    evidence_path: Path,
    decisions_path: Path | None = None,
) -> dict[str, object]:
    """Build a portable review-bundle manifest without embedding file contents."""

    spec_dir = spec_dir.resolve()
    examples_dir = spec_dir / "examples"
    entries = [
        *[_file_entry("spec_required", spec_dir / relative_path) for relative_path in REQUIRED_SPEC_FILES],
        *[_file_entry("spec_example", examples_dir / relative_path) for relative_path in REQUIRED_EXAMPLE_FILES],
        *[_file_entry("spec_optional", spec_dir / relative_path) for relative_path in OPTIONAL_SPEC_FILES],
        _file_entry("active_policy", policy_path),
        _file_entry("active_candidate", candidate_path),
        _file_entry("active_evidence", evidence_path),
    ]
    if decisions_path is not None:
        entries.append(_file_entry("active_decisions", decisions_path))

    missing_required = [entry["path"] for entry in entries if _is_required(entry["role"]) and not entry["exists"]]
    return {
        "manifest_version": "1.0.0",
        "spec_dir": str(spec_dir),
        "complete": not missing_required,
        "total_files": len(entries),
        "present_files": sum(1 for entry in entries if entry["exists"]),
        "missing_required": missing_required,
        "files": entries,
    }


def format_bundle_manifest_text(manifest: dict[str, object]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Bundle Manifest",
            f"Manifest version: {manifest['manifest_version']}",
            f"Spec dir: {manifest['spec_dir']}",
            f"Complete: {manifest['complete']}",
            f"Present files: {manifest['present_files']}/{manifest['total_files']}",
            f"Missing required: {_inline_list(manifest['missing_required'])}",
        ]
    )


def format_bundle_manifest_markdown(manifest: dict[str, object]) -> str:
    file_lines = [
        f"- {entry['role']}: {entry['path']} ({'present' if entry['exists'] else 'missing'}, sha256={entry['sha256'] or 'none'})"
        for entry in manifest["files"]
    ]
    return "\n".join(
        [
            "# Energy Aware Code Bundle Manifest",
            "",
            f"- Manifest version: {manifest['manifest_version']}",
            f"- Spec dir: {manifest['spec_dir']}",
            f"- Complete: {manifest['complete']}",
            f"- Present files: {manifest['present_files']}/{manifest['total_files']}",
            "",
            "## Missing required",
            "",
            *_bullet_list(manifest["missing_required"]),
            "",
            "## Files",
            "",
            *file_lines,
            "",
        ]
    )


def _file_entry(role: str, path: Path) -> dict[str, object]:
    resolved = path.resolve()
    exists = resolved.is_file()
    return {
        "role": role,
        "path": str(resolved),
        "exists": exists,
        "size_bytes": resolved.stat().st_size if exists else None,
        "sha256": _sha256(resolved) if exists else None,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_required(role: object) -> bool:
    return role in {
        "spec_required",
        "spec_example",
        "active_policy",
        "active_candidate",
        "active_evidence",
        "active_decisions",
    }


def _inline_list(items: object) -> str:
    if not isinstance(items, list) or not items:
        return "none"
    return ", ".join(str(item) for item in items)


def _bullet_list(items: object) -> list[str]:
    if not isinstance(items, list) or not items:
        return ["- none"]
    return [f"- {item}" for item in items]
