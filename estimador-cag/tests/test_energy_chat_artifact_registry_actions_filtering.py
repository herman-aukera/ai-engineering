from app.energy_chat.artifact_registry import artifact_paths


def test_artifact_registry_includes_actions_filtering_guide() -> None:
    assert "docs/energy_aware_chat_actions_filtering.md" in artifact_paths()
