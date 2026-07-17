import subprocess
import sys
from pathlib import Path


def test_reviewer_cli_outputs_markdown_from_project_root() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.reviewer_cli",
            "--project-root",
            ".",
            "--format",
            "markdown",
            "--fail-on-incomplete",
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "# Energy Aware Code Reviewer Snapshot" in completed.stdout
    assert "Complete: True" in completed.stdout


def test_reviewer_cli_outputs_markdown_from_repository_root() -> None:
    project_root = Path.cwd()
    repo_root = project_root.parent

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.reviewer_cli",
            "--project-root",
            "estimador-cag",
            "--format",
            "markdown",
            "--fail-on-incomplete",
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "# Energy Aware Code Reviewer Snapshot" in completed.stdout
    assert "Complete: True" in completed.stdout
