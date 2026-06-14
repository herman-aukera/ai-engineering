from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCRIPT = ROOT / "scripts/export_energy_chat_manifest.sh"


def test_export_manifest_lists_demo_command_checklist() -> None:
    text = MANIFEST_SCRIPT.read_text(encoding="utf-8")
    assert "docs/energy_aware_chat_demo_command_checklist.md" in text
