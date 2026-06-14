from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    output_dir = Path(tempfile.gettempdir()) / "eacode-standalone-scaffold-smoke"
    if output_dir.exists():
        shutil.rmtree(output_dir)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.scaffold_cli",
            "--project-root",
            str(project_root),
            "--output-dir",
            str(output_dir),
            "--format",
            "markdown",
            "--fail-on-incomplete",
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        return result.returncode

    required_files = [
        output_dir / "README.md",
        output_dir / "pyproject.toml",
        output_dir / ".gitignore",
        output_dir / "docs" / "EXTRACTION_NOTES.md",
        output_dir / "docs" / "COPY_MANIFEST.md",
        output_dir / "docs" / "VALIDATION_COMMANDS.md",
    ]
    missing = [str(path) for path in required_files if not path.is_file()]
    if missing:
        print("Missing scaffold files:", file=sys.stderr)
        for path in missing:
            print(f"- {path}", file=sys.stderr)
        return 1

    if "Complete: True" not in result.stdout:
        print(result.stdout)
        print("Scaffold output did not report Complete: True", file=sys.stderr)
        return 1

    print("Energy Core scaffold smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
