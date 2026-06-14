from pathlib import Path

INDEX = Path("docs/energy_aware_chat_reviewer_index.md").read_text(encoding="utf-8")


def test_reviewer_index_links_proof_packet() -> None:
    assert "docs/energy_aware_chat_final_project_proof_packet.md" in INDEX
    assert "Fast path for review" in INDEX
