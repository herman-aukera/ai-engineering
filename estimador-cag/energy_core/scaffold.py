from __future__ import annotations

from pathlib import Path
from typing import Any

from energy_core.package_manifest import build_package_manifest, format_package_manifest_markdown

SCAFFOLD_VERSION = "1.0.0"

SCAFFOLD_FILES = [
    "README.md",
    "pyproject.toml",
    ".gitignore",
    "docs/EXTRACTION_NOTES.md",
    "docs/COPY_MANIFEST.md",
    "docs/VALIDATION_COMMANDS.md",
]


def build_standalone_scaffold(project_root: Path, output_dir: Path) -> dict[str, Any]:
    """Write a deterministic standalone-repo scaffold without copying source files."""

    manifest = build_package_manifest(project_root)
    output = output_dir.resolve()
    docs_dir = output / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    writers = {
        "README.md": _readme,
        "pyproject.toml": _pyproject,
        ".gitignore": _gitignore,
        "docs/EXTRACTION_NOTES.md": lambda: _extraction_notes(manifest),
        "docs/COPY_MANIFEST.md": lambda: format_package_manifest_markdown(manifest),
        "docs/VALIDATION_COMMANDS.md": _validation_commands,
    }

    files: list[dict[str, Any]] = []
    missing: list[str] = []
    for relative_path, writer in writers.items():
        path = output / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(writer(), encoding="utf-8")
        exists = path.is_file()
        files.append(
            {
                "relative_path": relative_path,
                "path": str(path),
                "exists": exists,
                "size_bytes": path.stat().st_size if exists else None,
            }
        )
        if not exists:
            missing.append(relative_path)

    return {
        "scaffold_version": SCAFFOLD_VERSION,
        "output_dir": str(output),
        "complete": not missing and manifest["complete"],
        "files_total": len(files),
        "files_present": sum(1 for item in files if item["exists"]),
        "missing": missing,
        "files": files,
        "source_package_complete": manifest["complete"],
        "source_package_present": manifest["present_total"],
        "source_package_required": manifest["required_total"],
        "non_goals": [
            "Scaffold export does not copy source files automatically.",
            "Scaffold export does not execute shell actions.",
            "Scaffold export does not call LLM providers.",
            "Scaffold export does not create or push a repository.",
        ],
    }


def format_standalone_scaffold_text(scaffold: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Standalone Scaffold",
            f"Version: {scaffold['scaffold_version']}",
            f"Output dir: {scaffold['output_dir']}",
            f"Complete: {scaffold['complete']}",
            f"Files: {scaffold['files_present']}/{scaffold['files_total']}",
            f"Source package complete: {scaffold['source_package_complete']}",
            f"Missing: {_inline_list(scaffold['missing'])}",
        ]
    )


def format_standalone_scaffold_markdown(scaffold: dict[str, Any]) -> str:
    lines = [
        "# Energy Aware Code Standalone Scaffold",
        "",
        f"- Version: {scaffold['scaffold_version']}",
        f"- Output dir: {scaffold['output_dir']}",
        f"- Complete: {scaffold['complete']}",
        f"- Files: {scaffold['files_present']}/{scaffold['files_total']}",
        f"- Source package complete: {scaffold['source_package_complete']}",
        f"- Source package files: {scaffold['source_package_present']}/{scaffold['source_package_required']}",
        "",
        "## Missing",
        "",
    ]
    lines.extend(_bullet_list(scaffold["missing"]))
    lines.extend(["", "## Generated files", ""])
    for item in scaffold["files"]:
        status = "present" if item["exists"] else "missing"
        lines.append(f"- {item['relative_path']} ({status}, size={item['size_bytes'] or 0} bytes)")
    lines.extend(["", "## Non goals", ""])
    lines.extend(_bullet_list(scaffold["non_goals"]))
    return "\n".join(lines)


def _readme() -> str:
    return "\n".join(
        [
            "# EACODE",
            "",
            "Energy Aware Code validates coding-agent steps before they are accepted.",
            "",
            "Core transition:",
            "",
            "```text",
            "spec + policy + candidate_state + evidence",
            "→ deterministic critics",
            "→ energy score",
            "→ decider",
            "→ accept | repair | reject | escalate",
            "→ append decision to ledger",
            "```",
            "",
            "This scaffold is generated from the AI Engineering incubator branch.",
            "Copy source files according to `docs/COPY_MANIFEST.md` before treating it as standalone.",
        ]
    )


def _pyproject() -> str:
    return "\n".join(
        [
            "[project]",
            'name = "eacode"',
            'version = "0.1.0"',
            'description = "Energy Aware Code deterministic judge"',
            'requires-python = ">=3.11"',
            "dependencies = [",
            '    "pydantic>=2.0",',
            '    "pyyaml>=6.0",',
            "]",
            "",
            "[project.optional-dependencies]",
            "dev = [",
            '    "ruff>=0.9.0",',
            '    "pytest>=8.3.0",',
            "]",
            "",
            "[tool.ruff]",
            "line-length = 100",
            'target-version = "py311"',
            "",
            "[tool.ruff.lint]",
            'select = ["E", "F", "I", "N", "W", "UP"]',
        ]
    )


def _gitignore() -> str:
    return "\n".join(
        [
            "__pycache__/",
            "*.py[cod]",
            ".pytest_cache/",
            ".ruff_cache/",
            ".venv/",
            "dist/",
            "build/",
            "*.egg-info/",
            ".env",
            ".env.*",
            "!.env.example",
        ]
    )


def _extraction_notes(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Extraction Notes",
            "",
            "This scaffold is a generated target shape, not a completed extraction.",
            "",
            f"Source package complete: {manifest['complete']}",
            f"Source package files present: {manifest['present_total']}/{manifest['required_total']}",
            "",
            "## Manual extraction steps",
            "",
            "1. Create the standalone repository.",
            "2. Copy roots listed in `docs/COPY_MANIFEST.md`.",
            "3. Recreate CI around the Energy Core full gate.",
            "4. Run the full gate before publishing.",
            "5. Keep adapter execution out until the deterministic judge is stable.",
        ]
    )


def _validation_commands() -> str:
    return "\n".join(
        [
            "# Validation Commands",
            "",
            "Run after copying the package into the future standalone repository:",
            "",
            "```bash",
            "uv run ruff check --fix energy_core tests scripts",
            "uv run ruff check energy_core tests scripts",
            "uv run python -m py_compile $(find energy_core tests scripts -name '*.py' -type f)",
            "uv run pytest -q",
            "```",
            "",
            "The incubator branch currently provides a stronger full-gate script.",
        ]
    )


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]
