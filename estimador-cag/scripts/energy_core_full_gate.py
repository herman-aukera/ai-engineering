from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GateCommand:
    label: str
    cwd: Path
    argv: tuple[str, ...]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _python_files(project_root: Path) -> list[str]:
    roots = [project_root / "energy_core", project_root / "tests", project_root / "scripts"]
    files: list[str] = []
    for root in roots:
        if root.exists():
            files.extend(str(path.relative_to(project_root)) for path in root.rglob("*.py"))
    return sorted(files)


def build_gate_commands(*, include_ruff_fix: bool) -> list[GateCommand]:
    repo_root = _repo_root()
    project_root = _project_root()
    py_files = _python_files(project_root)

    commands: list[GateCommand] = []
    if include_ruff_fix:
        commands.append(
            GateCommand(
                "Ruff autofix",
                project_root,
                ("uv", "run", "ruff", "check", "--fix", "energy_core", "tests", "scripts"),
            )
        )
    commands.extend(
        [
            GateCommand(
                "Ruff check",
                project_root,
                ("uv", "run", "ruff", "check", "energy_core", "tests", "scripts"),
            ),
            GateCommand(
                "Python compile",
                project_root,
                ("uv", "run", "python", "-m", "py_compile", *py_files),
            ),
            GateCommand(
                "Energy Core boundary",
                project_root,
                ("uv", "run", "python", "scripts/energy_core_boundary_check.py"),
            ),
            GateCommand("Pytest", project_root, ("uv", "run", "pytest", "-q")),
            GateCommand("Energy Core smoke", project_root, ("uv", "run", "python", "scripts/energy_core_smoke.py")),
            GateCommand(
                "Energy Core example smoke",
                project_root,
                ("uv", "run", "python", "scripts/energy_core_example_smoke.py"),
            ),
            GateCommand(
                "Energy Core constraint smoke",
                project_root,
                ("uv", "run", "python", "scripts/energy_core_constraint_smoke.py"),
            ),
            GateCommand(
                "Energy Core release smoke",
                project_root,
                ("uv", "run", "python", "scripts/energy_core_release_smoke.py"),
            ),
            GateCommand(
                "Energy Core schema smoke",
                project_root,
                ("uv", "run", "python", "scripts/energy_core_schema_smoke.py"),
            ),
            GateCommand(
                "Energy Core package smoke",
                project_root,
                ("uv", "run", "python", "scripts/energy_core_package_smoke.py"),
            ),
            GateCommand(
                "Energy Core reviewer smoke",
                project_root,
                ("uv", "run", "python", "scripts/energy_core_reviewer_smoke.py"),
            ),
            GateCommand(
                "Energy Core command catalog smoke",
                project_root,
                ("uv", "run", "python", "scripts/energy_core_command_catalog_smoke.py"),
            ),
            GateCommand(
                "Energy Core root smoke",
                repo_root,
                (str(repo_root / "estimador-cag/.venv/bin/python"), "scripts/energy_core_root_smoke.py"),
            ),
            GateCommand("Git diff check", repo_root, ("git", "diff", "--check")),
            GateCommand("Git status check", repo_root, ("git", "status", "--short")),
        ]
    )
    return commands


def _run(command: GateCommand) -> None:
    print(f"=== {command.label} ===", flush=True)
    completed = subprocess.run(command.argv, cwd=command.cwd, text=True, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    if command.label == "Git status check":
        status = subprocess.run(
            command.argv,
            cwd=command.cwd,
            text=True,
            check=False,
            capture_output=True,
        )
        if status.stdout.strip():
            print(status.stdout, end="")
            raise SystemExit("Repository is dirty after full gate.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the full Energy Core validation gate.")
    parser.add_argument("--fix", action="store_true", help="Run Ruff autofix before the read-only gates.")
    args = parser.parse_args(argv)

    for command in build_gate_commands(include_ruff_fix=args.fix):
        _run(command)

    print("Energy Core full gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
