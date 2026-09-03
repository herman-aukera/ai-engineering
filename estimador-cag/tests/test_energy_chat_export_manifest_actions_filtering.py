import shutil
import subprocess
import sys
from pathlib import Path


def _bash_executable() -> str:
    if sys.platform == "win32":
        git = shutil.which("git")
        if git:
            candidate = Path(git).resolve().parents[1] / "bin" / "bash.exe"
            if candidate.is_file():
                return str(candidate)
    return "bash"


def test_export_manifest_includes_actions_filtering_guide() -> None:
    result = subprocess.run(
        [_bash_executable(), "scripts/export_energy_chat_manifest.sh"],
        check=True,
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )

    assert "docs/energy_aware_chat_actions_filtering.md" in result.stdout
