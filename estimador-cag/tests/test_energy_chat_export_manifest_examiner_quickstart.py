from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCRIPT = ROOT / "scripts/export_energy_chat_manifest.sh"


def test_export_manifest_lists_examiner_quickstart() -> None:
    text = MANIFEST_SCRIPT.read_text(encoding="utf-8")
    assert "docs/energy_aware_chat_examiner_quickstart.md" in text
