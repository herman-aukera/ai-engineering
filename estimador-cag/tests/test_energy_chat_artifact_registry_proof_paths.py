from app.energy_chat.artifact_registry import artifact_paths


def test_artifact_registry_lists_proof_paths() -> None:
    paths = artifact_paths()

    assert "docs/energy_aware_chat_final_project_proof_packet.md" in paths
    assert "scripts/render_energy_chat_release_snapshot.py" in paths
