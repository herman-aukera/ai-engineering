from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    repo_root = project_root.parent

    with tempfile.TemporaryDirectory(prefix="eacode-review-pack-") as temp_dir:
        output_dir = Path(temp_dir) / "pack"
        command = [
            sys.executable,
            "-m",
            "energy_core.review_pack_cli",
            "--project-root",
            "estimador-cag",
            "--output-dir",
            str(output_dir),
            "--format",
            "markdown",
            "--fail-on-incomplete",
        ]
        result = subprocess.run(
            command,
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=True,
        )

        required = [
            "README.md",
            "reviewer_snapshot.md",
            "release_readiness.md",
            "package_manifest.md",
            "export_plan.md",
            "command_catalog.md",
            "critic_coverage.md",
            "ledger_integrity.md",
        ]
        for filename in required:
            path = output_dir / filename
            if not path.is_file() or path.stat().st_size == 0:
                raise AssertionError(f"Review pack artifact missing or empty: {path}")

        if "# Energy Aware Code Review Pack" not in result.stdout:
            raise AssertionError("Review pack Markdown heading is missing.")
        if "Complete: True" not in result.stdout:
            raise AssertionError("Review pack did not report complete output.")

    print("Energy Core review pack smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
