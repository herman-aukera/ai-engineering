from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent


def test_energy_chat_deployment_assets_exist_and_are_secret_safe() -> None:
    dockerfile = ROOT / "Dockerfile.energy-chat"
    compose = ROOT / "docker-compose.energy-chat.yml"
    start_script = ROOT / "scripts" / "start_energy_chat.sh"
    live_smoke = ROOT / "scripts" / "smoke_energy_chat_live_provider.py"
    workflow = REPO_ROOT / ".github" / "workflows" / "energy-chat-live-provider-smoke.yml"

    for path in [dockerfile, compose, start_script, live_smoke, workflow]:
        assert path.exists(), path
        text = path.read_text(encoding="utf-8")
        assert "replace-with-provider-key" not in text
        assert "sk-" not in text


def test_energy_chat_deployment_doc_keeps_claim_boundary() -> None:
    doc = (ROOT / "docs" / "energy_aware_chat_mvp_upgrade.md").read_text(encoding="utf-8")

    assert "production-oriented MVP candidate" in doc
    assert "not production-ready" in doc
    assert "POST /energy-chat/chat" in doc
    assert "POST /energy-chat/rag/search" in doc
    assert "measurement_only_no_quality_claim" in doc
    assert "quality improvement over DeepSeek is proven" in doc


def test_live_provider_workflow_is_manual_only() -> None:
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "energy-chat-live-provider-smoke.yml"
    ).read_text(encoding="utf-8")

    assert "workflow_dispatch" in workflow
    assert "push:" not in workflow
    assert "DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}" in workflow
    assert "KIMI_API_KEY: ${{ secrets.KIMI_API_KEY }}" in workflow
