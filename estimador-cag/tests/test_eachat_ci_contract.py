from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def test_blocking_eachat_ci_is_keyless_and_runs_contract_plus_smoke() -> None:
    ci = _read(".github/workflows/energy-chat-ci.yml")

    assert "branches:\n      - EACHAT" in ci
    assert '${{ secrets.' not in ci
    assert "bash scripts/validate_energy_chat.sh" in ci
    assert "tests/test_eachat_session15_production_contract.py" in ci
    assert "tests/smoke/test_eachat_production_smoke.py" in ci
    assert "smoke_eachat_live_provider.py" not in ci
    assert "--live" not in ci


def test_container_canary_is_real_postgres_restart_integration() -> None:
    canary = _read(".github/workflows/eachat-container-canary.yml")

    assert "branches:\n      - EACHAT" in canary
    assert "uv lock --project deploy/eachat --check" in canary
    assert "EACHAT_POSTGRES_URL=postgresql://" in canary
    assert '--env GIT_SHA="$EXPECTED_HEAD_SHA"' in canary
    for path in ("/startup", "/health", "/ready", "/version"):
        assert path in canary
    assert "Seed durable two-turn conversation" in canary
    assert "Recreate application container against the same database" in canary
    assert "Verify restart recovery" in canary
    assert "restart_persistent" in canary
    assert "conversation_restart_persistent" in canary
    assert "strict_msgpack" in canary


def test_live_provider_workflow_is_manual_and_separate() -> None:
    live = _read(".github/workflows/eachat-live-provider-smoke.yml")

    assert "workflow_dispatch:" in live
    assert "smoke_eachat_live_provider.py" in live
    assert "--live" in live
    assert '${{ secrets.' in live


def test_release_workflow_is_keyless_and_immutable() -> None:
    release = _read(".github/workflows/eachat-release-image.yml")

    assert "workflow_dispatch:" in release
    assert "uv lock --project deploy/eachat --check" in release
    assert "push: true" in release
    assert "${{ github.sha }}" in release
    assert "steps.build.outputs.digest" in release
    assert "OPENAI_API_KEY" not in release
    assert "DEEPSEEK_API_KEY" not in release
    assert "KIMI_API_KEY" not in release
