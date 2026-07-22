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


def test_live_route_does_not_use_fallback_method_by_default(monkeypatch) -> None:
    calls = {"direct": 0, "fallback": 0}

    class FallbackSpy:
        def complete_messages(self, *, messages, tier, max_tokens):
            calls["direct"] += 1
            return {
                "estimation": (
                    "Decision: use direct DeepSeek. Evidence: direct call. "
                    "Next action: verify no fallback."
                ),
                "provider": "deepseek",
                "model": "deepseek-v4-flash",
                "tier": "flash",
                "fallback_used": False,
            }

        def complete_with_fallback_messages(self, **kwargs):
            calls["fallback"] += 1
            raise AssertionError("fallback method must not run by default")

    monkeypatch.setattr(
        "app.energy_chat.baseline._build_default_provider",
        lambda: FallbackSpy(),
    )
    response = client.post(
        "/energy-chat/v2/chat/live",
        json={"user_message": "test no fallback default"},
    )
    assert response.status_code == 200
    assert calls == {"direct": 1, "fallback": 0}
    assert response.json()["fallback_used"] is False


def test_explicit_allowlisted_fallback_is_projected_and_ledgered(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class ExplicitFallbackProvider:
        def complete_messages(self, **kwargs):
            raise AssertionError("explicit fallback path should use the ladder method")

        def complete_with_fallback_messages(
            self, *, messages, starting_tier, tier_ladder, max_tokens
        ):
            captured["starting_tier"] = starting_tier
            captured["tier_ladder"] = tier_ladder
            return {
                "estimation": (
                    "Decision: use authorized Kimi fallback. Evidence: fallback. "
                    "Next action: inspect the audit references."
                ),
                "provider": "kimi",
                "model": "kimi-backup-test",
                "tier": "backup",
                "fallback_used": True,
            }

    monkeypatch.setattr(
        "app.energy_chat.baseline._build_default_provider",
        lambda: ExplicitFallbackProvider(),
    )
    response = client.post(
        "/energy-chat/v2/chat/live",
        json={
            "user_message": "test authorized fallback",
            "allow_provider_fallback": True,
            "fallback_provider_allowlist": ["kimi"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert captured["tier_ladder"] == ["flash", "backup", "backup_pro"]
    assert body["served_provider"] == "kimi"
    assert body["fallback_used"] is True
    assert body["fallback_authorized"] is True
    assert body["fallback_provider_allowlist"] == ["kimi"]
    assert "authorized fallback" in body["routing_reason"]
    assert "fallback_to:kimi" in body["evidence_refs"]
    assert body["ledger_entry_ids"]


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
