from app.energy_chat.artifact_registry import artifact_paths


def test_artifact_registry_includes_final_submission_handoff() -> None:
    assert "docs/energy_aware_chat_final_submission_handoff.md" in artifact_paths()
