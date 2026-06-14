from app.energy_chat.artifact_registry import artifact_paths


def test_artifact_registry_lists_mvp_paths() -> None:
    paths = artifact_paths()

    assert "docs/energy_aware_chat_mvp_upgrade.md" in paths
    assert "scripts/smoke_energy_chat_live_provider.py" in paths
    assert "scripts/start_energy_chat.sh" in paths
    assert "Dockerfile.energy-chat" in paths
    assert "docker-compose.energy-chat.yml" in paths
    assert "../.github/workflows/energy-chat-live-provider-smoke.yml" in paths
