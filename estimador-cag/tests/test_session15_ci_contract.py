from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def test_blocking_ci_is_explicitly_deterministic_and_tdd_layered() -> None:
    ci = _read(".github/workflows/ci.yml")

    assert "gg-session-14/plus-consolidated" in ci
    assert '${{ secrets.' not in ci
    assert 'uv run pytest -q -m "not live_provider"' in ci
    assert "tests/smoke/test_session15_http_smoke.py" in ci
    assert "tests/integration/test_session14_postgres_human_review.py" in ci
    assert 'RUN_SESSION14_POSTGRES_INTEGRATION: "1"' in ci
    assert "provider_readiness_benchmark.py" not in ci
    assert "-m live_provider" not in ci


def test_container_smoke_proves_release_identity_and_all_lifecycle_probes() -> None:
    ci = _read(".github/workflows/ci.yml")

    for path in (
        "/startup",
        "/health",
        "/ready",
        "/version",
        "/api/v1/estimate/graph/unified/readiness",
    ):
        assert path in ci
    assert '--env GIT_SHA=' in ci
    assert "docker exec estimador-cag id -u" in ci


def test_real_provider_evaluation_is_non_blocking_and_manual() -> None:
    evaluation = _read(".github/workflows/provider-evaluation.yml")

    assert "workflow_dispatch:" in evaluation
    assert "provider_readiness_benchmark.py" in evaluation
    assert '${{ secrets.' in evaluation
    assert "pull_request:" not in evaluation


def test_release_build_remains_keyless_and_immutable() -> None:
    release = _read(".github/workflows/release-image.yml")

    assert "workflow_dispatch:" in release
    assert "packages: write" in release
    assert "push: true" in release
    assert "${{ github.sha }}" in release
    assert "steps.build.outputs.digest" in release
    assert "OPENAI_API_KEY" not in release
    assert "DEEPSEEK_API_KEY" not in release
    assert "KIMI_API_KEY" not in release
