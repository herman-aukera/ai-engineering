from app.energy_chat.artifact_registry import artifact_paths


def test_artifact_registry_lists_required_paths() -> None:
    paths = artifact_paths()

    assert "app/energy_chat/" in paths
    assert "energy_chat_streamlit_app.py" in paths
    assert "demo_payloads/energy_chat/" in paths
    assert "docs/energy_aware_chat_reviewer_index.md" in paths
