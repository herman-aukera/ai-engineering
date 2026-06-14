from app.energy_chat.artifact_registry import artifact_paths


def test_artifact_registry_lists_demo_command_checklist() -> None:
    assert "docs/energy_aware_chat_demo_command_checklist.md" in artifact_paths()
