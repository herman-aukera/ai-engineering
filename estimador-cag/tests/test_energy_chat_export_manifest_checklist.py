import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_export_manifest_includes_demo_evidence_checklist() -> None:
    result = subprocess.run(
        ["bash", "scripts/export_energy_chat_manifest.sh"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "docs/energy_aware_chat_demo_evidence_checklist.md" in result.stdout
