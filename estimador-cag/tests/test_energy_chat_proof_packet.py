from pathlib import Path

PROOF_PACKET = Path("docs/energy_aware_chat_final_project_proof_packet.md").read_text(
    encoding="utf-8"
)


def test_final_project_proof_packet_points_to_reviewer_path() -> None:
    assert "energy_aware_chat_reviewer_index.md" in PROOF_PACKET
    assert "energy_aware_chat_live_demo_readiness.md" in PROOF_PACKET
    assert "energy_aware_chat_release_snapshot.md" in PROOF_PACKET
    assert "demo_payloads/energy_chat/" in PROOF_PACKET


def test_final_project_proof_packet_keeps_claim_boundary() -> None:
    assert "does not claim production readiness" in PROOF_PACKET
    assert "RAG grounding" in PROOF_PACKET
    assert "live model quality improvement" in PROOF_PACKET
