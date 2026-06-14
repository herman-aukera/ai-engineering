from app.energy_chat.artifact_registry import artifact_paths


def test_artifact_registry_lists_examiner_quickstart() -> None:
    assert "docs/energy_aware_chat_examiner_quickstart.md" in artifact_paths()
