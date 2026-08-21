from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def test_blocking_eacode_ci_is_keyless_and_has_explicit_test_layers() -> None:
    ci = _read(".github/workflows/ci.yml")

    assert "- EACODE" in ci
    assert '${{ secrets.' not in ci
    assert 'uv run pytest -q -m "not live_provider"' in ci
    assert "tests/test_eacode_session15_production_contract.py" in ci
    assert "tests/smoke/test_eacode_production_smoke.py" in ci
    assert "energy_core_live_provider_smoke.py" not in ci


def test_container_integration_exercises_public_v1_control_plane() -> None:
    ci = _read(".github/workflows/ci.yml")

    assert "eacode-production-envelope" in ci
    for path in (
        "/startup",
        "/health",
        "/ready",
        "/version",
        "/api/v1/eacode/status",
        "/api/v1/eacode/capabilities",
        "/api/v1/eacode/select",
    ):
        assert path in ci
    assert "provider_selection" in ci
    assert "planned_only" in ci
    assert "served_provider_evidence" in ci
    assert "docker exec eacode-canary id -u" in ci


def test_live_provider_smoke_is_manual_and_separate() -> None:
    live = _read(".github/workflows/live-smoke.yml")

    assert "workflow_dispatch:" in live
    assert "energy_core_live_provider_smoke.py" in live
    assert '${{ secrets.' in live


def test_release_is_manual_keyless_and_digest_addressable() -> None:
    release = _read(".github/workflows/eacode-release-image.yml")

    assert "workflow_dispatch:" in release
    assert "push: true" in release
    assert "${{ github.sha }}" in release
    assert "steps.image.outputs.digest" in release
    assert "OPENAI_API_KEY" not in release
    assert "DEEPSEEK_API_KEY" not in release
    assert "KIMI_API_KEY" not in release
