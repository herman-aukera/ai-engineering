from pathlib import Path

from app.energy_chat.artifact_registry import artifact_paths

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "docs" / "energy_aware_chat_demo_script.md").read_text(
    encoding="utf-8"
)
INDEX = (ROOT / "docs" / "energy_aware_chat_reviewer_index.md").read_text(
    encoding="utf-8"
)
MANIFEST = (ROOT / "scripts" / "export_energy_chat_manifest.sh").read_text(
    encoding="utf-8"
)


def test_demo_script_has_proof_commands_and_claim_token() -> None:
    assert "bash scripts/validate_energy_chat.sh" in SCRIPT
    assert "bash estimador-cag/scripts/check_energy_chat_ci.sh" in SCRIPT
    assert "measurement_only_no_quality_claim" in SCRIPT


def test_demo_script_is_linked_from_reviewer_surfaces() -> None:
    path = "docs/energy_aware_chat_demo_script.md"
    assert path in INDEX
    assert path in MANIFEST
    assert path in artifact_paths()
