from __future__ import annotations

from pathlib import Path

REQUIRED_SPEC_FILES = [
    "requirements.md",
    "design.md",
    "tasks.md",
    "acceptance.md",
    "energy-policy.yaml",
    "evidence.jsonl",
]

REQUIRED_EXAMPLE_FILES = [
    "candidate_accept.json",
    "candidate_repair_missing_evidence.json",
    "candidate_reject_tests_failed.json",
    "candidate_reject_scope_creep.json",
]

OPTIONAL_SPEC_FILES = [
    "decisions.jsonl",
]


def summarize_spec_package(spec_dir: Path) -> dict[str, object]:
    spec_dir = spec_dir.resolve()
    examples_dir = spec_dir / "examples"

    required_files = _status_by_relative_path(spec_dir, REQUIRED_SPEC_FILES)
    example_files = _status_by_relative_path(examples_dir, REQUIRED_EXAMPLE_FILES)
    optional_files = _status_by_relative_path(spec_dir, OPTIONAL_SPEC_FILES)

    missing_required = [name for name, present in required_files.items() if not present]
    missing_examples = [f"examples/{name}" for name, present in example_files.items() if not present]
    missing = [*missing_required, *missing_examples]

    total_required = len(REQUIRED_SPEC_FILES) + len(REQUIRED_EXAMPLE_FILES)
    present_required = total_required - len(missing)

    return {
        "spec_dir": str(spec_dir),
        "complete": not missing,
        "present_required": present_required,
        "total_required": total_required,
        "required_files": required_files,
        "example_files": example_files,
        "optional_files": optional_files,
        "missing": missing,
    }


def _status_by_relative_path(base_dir: Path, relative_paths: list[str]) -> dict[str, bool]:
    return {relative_path: _is_present(base_dir / relative_path) for relative_path in relative_paths}


def _is_present(path: Path) -> bool:
    return path.exists() and path.is_file()
