import subprocess
import sys
from pathlib import Path


def test_review_pack_cli_writes_pack(tmp_path: Path) -> None:
    output_dir = tmp_path / "pack"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.review_pack_cli",
            "--output-dir",
            str(output_dir),
            "--format",
            "markdown",
            "--fail-on-incomplete",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=True,
    )

    assert "# Energy Aware Code Review Pack" in result.stdout
    assert "Complete: True" in result.stdout
    assert (output_dir / "README.md").is_file()
    assert (output_dir / "reviewer_snapshot.md").is_file()


def test_review_pack_cli_works_from_repo_root(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    output_dir = tmp_path / "root-pack"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.review_pack_cli",
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
        check=True,
    )

    assert "Energy Aware Code Review Pack" in result.stdout
    assert "Complete: True" in result.stdout
    assert (output_dir / "command_catalog.md").is_file()
