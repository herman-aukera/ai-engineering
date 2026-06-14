from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_energy_core_boundary_script_passes() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/energy_core_boundary_check.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Energy Core boundary check passed." in result.stdout


def test_energy_core_imports_without_course_app_runtime() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import energy_core; print(','.join(sorted(energy_core.__all__)))",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "EnergyDecision" in result.stdout
