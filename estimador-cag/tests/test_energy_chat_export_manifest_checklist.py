import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _bash_executable() -> str:
    if sys.platform == "win32":
        git = shutil.which("git")
        if git:
            candidate = Path(git).resolve().parents[1] / "bin" / "bash.exe"
            if candidate.is_file():
                return str(candidate)
    return "bash"


def test_export_manifest_includes_demo_evidence_checklist() -> None:
    result = subprocess.run(
        [_bash_executable(), "scripts/export_energy_chat_manifest.sh"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "docs/energy_aware_chat_demo_evidence_checklist.md" in result.stdout
