from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = (ROOT / "docs/energy_aware_chat_demo_command_checklist.md").read_text(
    encoding="utf-8"
)


def test_demo_command_checklist_lists_required_commands() -> None:
    assert "bash scripts/validate_energy_chat.sh" in CHECKLIST
    assert "bash estimador-cag/scripts/check_energy_chat_ci.sh" in CHECKLIST
    assert "streamlit run energy_chat_streamlit_app.py" in CHECKLIST


def test_demo_command_checklist_lists_payloads_and_claim_boundary() -> None:
    assert "demo_payloads/energy_chat/evaluate_accept.json" in CHECKLIST
    assert "demo_payloads/energy_chat/benchmark_measurement.json" in CHECKLIST
    assert "measurement_only_no_quality_claim" in CHECKLIST
