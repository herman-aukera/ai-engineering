from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = (ROOT / "docs" / "energy_aware_chat_final_submission_handoff.md").read_text(
    encoding="utf-8"
)
INDEX = (ROOT / "docs" / "energy_aware_chat_reviewer_index.md").read_text(
    encoding="utf-8"
)


def test_final_submission_handoff_has_required_commands() -> None:
    assert "EACHAT" in HANDOFF
    assert "bash scripts/validate_energy_chat.sh" in HANDOFF
    assert "bash estimador-cag/scripts/check_energy_chat_ci.sh" in HANDOFF
    assert "Energy Aware Chat CI" in HANDOFF


def test_final_submission_handoff_keeps_claim_boundary() -> None:
    assert "measurement_only_no_quality_claim" in HANDOFF
    assert "Do not claim production readiness" in HANDOFF
    assert "deterministic RAG grounding baseline" in HANDOFF
    assert "model quality improvement" in HANDOFF


def test_reviewer_index_opens_with_examiner_then_milestone_packet() -> None:
    fast_path = INDEX.split("## Fast path for review", maxsplit=1)[1]
    expected_items = [
        "1. `docs/energy_aware_chat_examiner_quickstart.md`",
        "2. `docs/energy_aware_chat_final_project_acceptance_matrix.md`",
        "3. `docs/energy_aware_chat_mvp_upgrade.md`",
        "4. `docs/energy_aware_chat_deployment_readiness_runbook.md`",
        "5. `docs/energy_aware_chat_live_provider_evidence_template.md`",
        "6. `docs/energy_aware_chat_mvp_demo_recording_packet.md`",
        "7. `docs/energy_aware_chat_final_submission_handoff.md`",
    ]

    for item in expected_items:
        assert item in fast_path
