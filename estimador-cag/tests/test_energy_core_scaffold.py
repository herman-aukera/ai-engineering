from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from energy_core.scaffold import build_standalone_scaffold
from energy_core.scaffold_cli import main


def test_standalone_scaffold_writes_expected_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "eacode"

    scaffold = build_standalone_scaffold(Path("."), output_dir)

    assert scaffold["complete"] is True
    assert scaffold["files_present"] == scaffold["files_total"]
    assert (output_dir / "README.md").is_file()
    assert (output_dir / "pyproject.toml").is_file()
    assert (output_dir / "docs" / "COPY_MANIFEST.md").is_file()
    assert "name = \"eacode\"" in (output_dir / "pyproject.toml").read_text(encoding="utf-8")


def test_scaffold_cli_outputs_markdown(tmp_path: Path, capsys) -> None:
    output_dir = tmp_path / "eacode"

    exit_code = main(
        [
            "--project-root",
            ".",
            "--output-dir",
            str(output_dir),
            "--format",
            "markdown",
            "--fail-on-incomplete",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "# Energy Aware Code Standalone Scaffold" in output
    assert "Complete: True" in output


def test_scaffold_cli_runs_from_repository_root(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    output_dir = tmp_path / "eacode"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.scaffold_cli",
            "--project-root",
            "estimador-cag",
            "--output-dir",
            str(output_dir),
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
    assert "Energy Aware Code Standalone Scaffold" in result.stdout
    assert "Complete: True" in result.stdout
    assert (output_dir / "README.md").is_file()
