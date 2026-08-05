from pathlib import Path

PROOF_PACKET = Path("docs/energy_aware_chat_final_project_proof_packet.md").read_text(
    encoding="utf-8"
)


def test_proof_packet_links_actions_filtering_guide() -> None:
    assert "docs/energy_aware_chat_actions_filtering.md" in PROOF_PACKET
    assert "unrelated runs from other branches" in PROOF_PACKET
