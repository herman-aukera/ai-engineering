from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUICKSTART = (ROOT / "docs/energy_aware_chat_examiner_quickstart.md").read_text(
    encoding="utf-8"
)


def test_examiner_quickstart_names_exact_branch_and_workflow() -> None:
    assert "gg-finalproject-energy-aware-chat" in QUICKSTART
    assert "Energy Aware Chat CI" in QUICKSTART
    assert "current HEAD" in QUICKSTART


def test_examiner_quickstart_points_to_validation_commands() -> None:
    assert "bash scripts/validate_energy_chat.sh" in QUICKSTART
    assert "bash estimador-cag/scripts/check_energy_chat_ci.sh" in QUICKSTART
    assert "measurement_only_no_quality_claim" in QUICKSTART
