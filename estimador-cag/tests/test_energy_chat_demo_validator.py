import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_demo_payload_validator_runs_from_project_root() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate_energy_chat_demo_payloads.py"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Energy Chat demo payload contracts passed." in result.stdout
