"""Regression tests for the independently audited Milestone 10 defects."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.energy_chat.candidate_provider import (
    CandidateGenerationResult,
    CandidateProviderRequest,
)
from app.energy_chat.graph_state import ProviderMetrics
from app.main import app

client = TestClient(app)


def test_deterministic_route_rejects_live_execution_profile() -> None:
    response = client.post(
        "/energy-chat/v2/chat",
        json={
            "user_message": "test route ownership",
            "execution_profile": "live_bounded",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "unsupported_execution_profile"


def test_live_route_rejects_deterministic_execution_profile() -> None:
    response = client.post(
        "/energy-chat/v2/chat/live",
        json={
            "user_message": "test route ownership",
            "execution_profile": "deterministic",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "unsupported_execution_profile"


def test_live_route_owns_profile_when_caller_omits_it(monkeypatch) -> None:
    class FakeLiveProvider:
        def generate(
            self, request: CandidateProviderRequest
        ) -> CandidateGenerationResult:
            return CandidateGenerationResult(
                answer=(
                    "Decision: use the bounded live route. "
                    "Evidence: fake provider. Next action: inspect the ledger."
                ),
                evidence_refs=["provider:fake_live"],
                metrics=ProviderMetrics(
                    provider_call_id=request.provider_call_id,
                    provider="deepseek",
                    model="deepseek-v4-flash",
                    tier="flash",
                ),
            )

    monkeypatch.setattr(
        "app.energy_chat.graph_application.BaselineCandidateProvider",
        lambda: FakeLiveProvider(),
    )
    response = client.post(
        "/energy-chat/v2/chat/live",
        json={"user_message": "test omitted execution profile"},
    )
    assert response.status_code == 200
    assert response.json()["served_provider"] == "deepseek"


def test_live_route_uses_direct_verified_provider_without_fallback(monkeypatch) -> None:
    calls = {"direct": 0}

    class DirectProvider:
        def generate(
            self, request: CandidateProviderRequest
        ) -> CandidateGenerationResult:
            calls["direct"] += 1
            return CandidateGenerationResult(
                answer=(
                    "Decision: use direct DeepSeek. Evidence: direct call. "
                    "Next action: verify no fallback."
                ),
                evidence_refs=["provider:deepseek"],
                metrics=ProviderMetrics(
                    provider_call_id=request.provider_call_id,
                    provider="deepseek",
                    model="deepseek-v4-flash",
                    tier="flash",
                    fallback_used=False,
                ),
            )

    monkeypatch.setattr(
        "app.energy_chat.graph_application.BaselineCandidateProvider",
        lambda: DirectProvider(),
    )
    response = client.post(
        "/energy-chat/v2/chat/live",
        json={
            "user_message": "test no fallback default",
            "provider_preference": "deepseek",
        },
    )
    assert response.status_code == 200
    assert calls == {"direct": 1}
    assert response.json()["fallback_used"] is False


def test_cross_provider_fallback_fails_closed_on_isolated_v2_adapter(monkeypatch) -> None:
    def fail_if_provider_is_built():
        raise AssertionError("fallback rejection must happen before provider execution")

    monkeypatch.setattr(
        "app.energy_chat.graph_application.BaselineCandidateProvider",
        fail_if_provider_is_built,
    )
    response = client.post(
        "/energy-chat/v2/chat/live",
        json={
            "user_message": "test authorized fallback",
            "provider_preference": "deepseek",
            "allow_provider_fallback": True,
            "fallback_provider_allowlist": ["kimi"],
        },
    )
    assert response.status_code == 400
    body = response.json()["detail"]
    assert body["error"] == "provider_unavailable"
    assert "fallback" in body["detail"].casefold()


def test_fallback_allowlist_requires_explicit_authorization() -> None:
    response = client.post(
        "/energy-chat/v2/chat/live",
        json={
            "user_message": "invalid fallback contract",
            "fallback_provider_allowlist": ["kimi"],
        },
    )
    assert response.status_code == 422


def test_fallback_authorization_requires_nonempty_allowlist() -> None:
    response = client.post(
        "/energy-chat/v2/chat/live",
        json={
            "user_message": "invalid fallback contract",
            "allow_provider_fallback": True,
        },
    )
    assert response.status_code == 422


def test_awaiting_evidence_reports_no_provider_call() -> None:
    response = client.post(
        "/energy-chat/v2/chat",
        json={
            "user_message": "What is the latest DeepSeek pricing today?",
            "mode": "research",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["awaiting_evidence"] is True
    assert body["candidate_count"] == 0
    assert body["served_provider"] == "none"
    assert body["served_model"] is None
    assert body["fallback_used"] is False
    assert body["provider_metrics_summary"]["provider_call_count"] == 0
    assert "generation skipped pending evidence" in body["routing_reason"]


def test_v2_feature_flag_disables_api_and_demo_but_not_legacy(monkeypatch) -> None:
    monkeypatch.setenv("EACHAT_V2_ENABLED", "false")

    deterministic = client.post(
        "/energy-chat/v2/chat",
        json={"user_message": "disabled v2"},
    )
    live = client.post(
        "/energy-chat/v2/chat/live",
        json={"user_message": "disabled v2"},
    )
    demo = client.get("/energy-chat/v2/demo")
    legacy = client.post(
        "/energy-chat/chat",
        json={"user_message": "legacy remains available"},
    )

    assert deterministic.status_code == 404
    assert live.status_code == 404
    assert demo.status_code == 404
    assert legacy.status_code == 200


def test_invalid_v2_feature_flag_fails_closed(monkeypatch) -> None:
    monkeypatch.setenv("EACHAT_V2_ENABLED", "definitely")
    response = client.post(
        "/energy-chat/v2/chat",
        json={"user_message": "invalid feature flag"},
    )
    assert response.status_code == 404
