from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = (ROOT / "docs" / "energy_aware_chat_final_submission_handoff.md").read_text(
    encoding="utf-8"
)
INDEX = (ROOT / "docs" / "energy_aware_chat_reviewer_index.md").read_text(
    encoding="utf-8"
)


def test_final_submission_handoff_has_required_commands() -> None:
    assert "gg-finalproject-energy-aware-chat" in HANDOFF
    assert "bash scripts/validate_energy_chat.sh" in HANDOFF
    assert "bash estimador-cag/scripts/check_energy_chat_ci.sh" in HANDOFF
    assert "Energy Aware Chat CI" in HANDOFF


def test_final_submission_handoff_keeps_claim_boundary() -> None:
    assert "measurement_only_no_quality_claim" in HANDOFF
    assert "Do not claim production readiness" in HANDOFF
    assert "RAG grounding" in HANDOFF


def test_reviewer_index_opens_with_examiner_quickstart_then_handoff() -> None:
    fast_path = INDEX.split("## Fast path for review", maxsplit=1)[1]
    assert "1. `docs/energy_aware_chat_examiner_quickstart.md`" in fast_path
    assert "2. `docs/energy_aware_chat_final_submission_handoff.md`" in fast_path
