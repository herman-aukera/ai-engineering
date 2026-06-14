from __future__ import annotations

import argparse
import subprocess
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
    roots = [
        project_root / "energy_core",
        project_root / "tests",
        project_root / "scripts",
    ]
    files: list[str] = []
    for root in roots:
        if root.exists():
            files.extend(
                str(path.relative_to(project_root)) for path in root.rglob("*.py")
            )
    return sorted(files)


def _project_command(label: str, argv: tuple[str, ...]) -> GateCommand:
    return GateCommand(label, _project_root(), argv)


def _repo_command(label: str, argv: tuple[str, ...]) -> GateCommand:
    return GateCommand(label, _repo_root(), argv)


def build_gate_commands(*, include_ruff_fix: bool) -> list[GateCommand]:
    repo_root = _repo_root()
    project_root = _project_root()
    py_files = _python_files(project_root)

    commands: list[GateCommand] = []
    if include_ruff_fix:
        commands.append(
            _project_command(
                "Ruff autofix",
                (
                    "uv",
                    "run",
                    "ruff",
                    "check",
                    "--fix",
                    "energy_core",
                    "tests",
                    "scripts",
                ),
            )
        )
    commands.extend(
        [
            _project_command(
                "Ruff check",
                ("uv", "run", "ruff", "check", "energy_core", "tests", "scripts"),
            ),
            _project_command(
                "Python compile",
                ("uv", "run", "python", "-m", "py_compile", *py_files),
            ),
            _project_command(
                "Energy Core boundary",
                ("uv", "run", "python", "scripts/energy_core_boundary_check.py"),
            ),
            _project_command("Pytest", ("uv", "run", "pytest", "-q")),
            _project_command(
                "Energy Core smoke",
                ("uv", "run", "python", "scripts/energy_core_smoke.py"),
            ),
            _project_command(
                "Energy Core example smoke",
                ("uv", "run", "python", "scripts/energy_core_example_smoke.py"),
            ),
            _project_command(
                "Energy Core constraint smoke",
                ("uv", "run", "python", "scripts/energy_core_constraint_smoke.py"),
            ),
            _project_command(
                "Energy Core critic coverage smoke",
                ("uv", "run", "python", "scripts/energy_core_critic_coverage_smoke.py"),
            ),
            _project_command(
                "Energy Core ledger integrity smoke",
                ("uv", "run", "python", "scripts/energy_core_ledger_integrity_smoke.py"),
            ),
            _project_command(
                "Energy Core nightly status smoke",
                ("uv", "run", "python", "scripts/energy_core_nightly_status_smoke.py"),
            ),
            _project_command(
                "Energy Core release smoke",
                ("uv", "run", "python", "scripts/energy_core_release_smoke.py"),
            ),
            _project_command(
                "Energy Core schema smoke",
                ("uv", "run", "python", "scripts/energy_core_schema_smoke.py"),
            ),
            _project_command(
                "Energy Core package smoke",
                ("uv", "run", "python", "scripts/energy_core_package_smoke.py"),
            ),
            _project_command(
                "Energy Core reviewer smoke",
                ("uv", "run", "python", "scripts/energy_core_reviewer_smoke.py"),
            ),
            _project_command(
                "Energy Core command catalog smoke",
                (
                    "uv",
                    "run",
                    "python",
                    "scripts/energy_core_command_catalog_smoke.py",
                ),
            ),
            _project_command(
                "Energy Core review pack smoke",
                ("uv", "run", "python", "scripts/energy_core_review_pack_smoke.py"),
            ),
            _project_command(
                "Energy Core scaffold smoke",
                ("uv", "run", "python", "scripts/energy_core_scaffold_smoke.py"),
            ),
            _project_command(
                "Energy Core export plan smoke",
                ("uv", "run", "python", "scripts/energy_core_export_plan_smoke.py"),
            ),
            _repo_command(
                "Energy Core root smoke",
                (
                    str(repo_root / "estimador-cag/.venv/bin/python"),
                    "scripts/energy_core_root_smoke.py",
                ),
            ),
            _repo_command("Git diff check", ("git", "diff", "--check")),
            _repo_command("Git status check", ("git", "status", "--short")),
        ]
    )
    return commands


def _run(command: GateCommand) -> None:
    print(f"=== {command.label} ===", flush=True)
    if command.label == "Git status check":
        status = subprocess.run(
            command.argv,
            cwd=command.cwd,
            text=True,
            check=False,
            capture_output=True,
        )
        if status.returncode != 0:
            raise SystemExit(status.returncode)
        if status.stdout.strip():
            print(status.stdout, end="")
            raise SystemExit("Repository is dirty after full gate.")
        return

    completed = subprocess.run(command.argv, cwd=command.cwd, text=True, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the full Energy Core validation gate."
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Run Ruff autofix before the read-only gates.",
    )
    args = parser.parse_args(argv)

    for command in build_gate_commands(include_ruff_fix=args.fix):
        _run(command)

    print("Energy Core full gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
