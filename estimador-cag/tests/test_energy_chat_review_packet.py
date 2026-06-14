from app.energy_chat.review_packet import build_review_packet


def test_review_packet_lists_open_first_docs() -> None:
    packet = build_review_packet()

    assert "docs/energy_aware_chat_reviewer_index.md" in packet.open_first
    assert "docs/energy_aware_chat_final_project_proof_packet.md" in packet.open_first
