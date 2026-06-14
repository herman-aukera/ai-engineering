from app.energy_chat.artifact_registry import artifact_paths


def test_artifact_registry_includes_pull_request_body_draft() -> None:
    assert "docs/energy_aware_chat_pr_body_draft.md" in artifact_paths()
