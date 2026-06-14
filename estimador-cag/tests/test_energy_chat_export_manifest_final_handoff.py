from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (ROOT / "scripts" / "export_energy_chat_manifest.sh").read_text(
    encoding="utf-8"
)


def test_export_manifest_includes_final_submission_handoff() -> None:
    assert "docs/energy_aware_chat_final_submission_handoff.md" in MANIFEST
