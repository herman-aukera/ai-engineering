import subprocess
from pathlib import Path


def test_export_manifest_includes_actions_filtering_guide() -> None:
    result = subprocess.run(
        ["bash", "scripts/export_energy_chat_manifest.sh"],
        check=True,
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )

    assert "docs/energy_aware_chat_actions_filtering.md" in result.stdout
