from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from energy_core.package_cli import main


def test_package_cli_outputs_text_from_project_root(capsys) -> None:
    exit_code = main(["--project-root", ".", "--format", "text", "--fail-on-incomplete"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Energy Aware Code Package Manifest" in output
    assert "Complete: True" in output


def test_package_cli_returns_nonzero_when_incomplete(tmp_path: Path, capsys) -> None:
    exit_code = main(
        [
            "--project-root",
            str(tmp_path),
            "--format",
            "text",
            "--fail-on-incomplete",
        ]
    )

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "Complete: False" in output


def test_package_cli_runs_from_repository_root() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.package_cli",
            "--project-root",
            "estimador-cag",
            "--format",
            "text",
            "--fail-on-incomplete",
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Energy Aware Code Package Manifest" in result.stdout
    assert "Complete: True" in result.stdout
