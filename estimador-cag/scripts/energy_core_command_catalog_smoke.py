from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run(command: list[object], cwd: Path) -> str:
    completed = subprocess.run(
        [str(part) for part in command],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr, file=sys.stderr)
        raise SystemExit(completed.returncode)
    return completed.stdout


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    repo_root = project_root.parent

    markdown = _run(
        [
            sys.executable,
            "-m",
            "energy_core.command_catalog_cli",
            "--format",
            "markdown",
            "--fail-on-incomplete",
        ],
        project_root,
    )
    if "# Energy Aware Code Command Catalog" not in markdown:
        print(markdown)
        print("Command catalog smoke did not print markdown title", file=sys.stderr)
        return 1
    if "Mutates ledger: True" not in markdown:
        print(markdown)
        print("Command catalog smoke did not expose ledger mutation behavior", file=sys.stderr)
        return 1

    root_text = _run(
        [
            repo_root / "estimador-cag" / ".venv" / "bin" / "python",
            "-m",
            "energy_core.command_catalog_cli",
            "--format",
            "text",
            "--fail-on-incomplete",
        ],
        repo_root,
    )
    if "Complete: True" not in root_text:
        print(root_text)
        print("Repo-root command catalog smoke did not report Complete: True", file=sys.stderr)
        return 1

    json_output = _run(
        [
            sys.executable,
            "-m",
            "energy_core.command_catalog_cli",
            "--format",
            "json",
            "--fail-on-incomplete",
        ],
        project_root,
    )
    payload = json.loads(json_output)
    if payload["mutating_command_ids"] != ["evaluate"]:
        print(json_output)
        print("Command catalog smoke found unexpected mutating commands", file=sys.stderr)
        return 1

    print("Energy Core command catalog smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
