"""Keyless proof for DeepSeek, Kimi Platform, and OpenAI adapter boundaries."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.energy_chat import graph_application
from app.energy_chat.candidate_provider import (
    CandidateGenerationResult,
    CandidateProviderRequest,
)
from app.energy_chat.graph_state import ProviderMetrics
from app.energy_chat.provider_adapters import (
    CatalogCandidateProvider,
    ProviderTransportResult,
    build_catalog_candidate_provider,
)
from app.energy_chat.provider_catalog import (
    KIMI_CODE_K3,
    ResolvedProviderProfile,
    resolve_effort_profile,
)
from app.energy_chat.runtime_container import EnergyChatApplicationRuntime
from app.main import app

client = TestClient(app)


class FakeTransport:
    def __init__(self, answer: str = "") -> None:
        self.answer = answer or (
            "The request is answered through an injected provider transport. "
            "The candidate remains subject to deterministic critics, scoring, and "
            "Decision Ledger projection. Next action: inspect the Energy Card."
        )
        self.calls: list[dict[str, object]] = []

    def complete(self, *, profile, messages, max_output_tokens):
        self.calls.append(
            {
                "profile": profile,
                "messages": messages,
                "max_output_tokens": max_output_tokens,
            }
        )
        return ProviderTransportResult(
            answer=self.answer,
            input_tokens=1_000,
            output_tokens=200,
            finish_reason="stop",
        )


class RouteFakeProvider:
    def __init__(self, provider: str, model: str) -> None:
        self.provider = provider
        self.model = model
        self.calls = 0

    def generate(self, request: CandidateProviderRequest) -> CandidateGenerationResult:
        self.calls += 1
        return CandidateGenerationResult(
            answer=(
                f"The {self.provider} candidate was generated through the selected "
                "provider adapter and remains governed by deterministic evaluation. "
                "Next action: review the recorded provider metrics."
            ),
            evidence_refs=request.evidence_refs,
            metrics=ProviderMetrics(
                provider_call_id=request.provider_call_id,
                provider=self.provider,
                model=self.model,
                tier="test",
                input_tokens=100,
                output_tokens=50,
                cost_usd=0.001,
                fallback_used=False,
            ),
        )


def test_catalog_adapter_calls_exact_transport_once_and_projects_cost() -> None:
    profile = resolve_effort_profile("kimi", "max")
    transport = FakeTransport()
    provider = CatalogCandidateProvider(profile=profile, transport=transport)

    result = provider.generate(
        CandidateProviderRequest(
            provider_call_id="call-kimi-max",
            user_request="Explain the architecture.",
            mode="project",
            max_tokens=800,
        )
    )

    assert len(transport.calls) == 1
    assert transport.calls[0]["profile"] == profile
    assert transport.calls[0]["max_output_tokens"] == 800
    assert result.metrics.provider == "kimi"
    assert result.metrics.model == "kimi-k3"
    assert result.metrics.tier == "max"
    assert result.metrics.input_tokens == 1_000
    assert result.metrics.output_tokens == 200
    assert result.metrics.cost_usd == pytest.approx(0.006)
    assert result.metrics.retries == 0
    assert result.metrics.fallback_used is False


def test_each_provider_builds_with_injected_transport_without_credentials() -> None:
    for provider_name, effort, expected_model in (
        ("deepseek", "fast", "deepseek-v4-flash"),
        ("kimi", "balanced", "kimi-k3"),
        ("openai", "max", "gpt-5.6-sol"),
    ):
        transport = FakeTransport()
        provider = build_catalog_candidate_provider(
            provider_name,
            effort,
            transport=transport,
            environment={},
        )
        assert provider.profile.capability.model_id == expected_model
        assert provider.transport is transport


def test_placeholder_credentials_fail_closed_without_network_calls() -> None:
    with pytest.raises(ValueError, match="non-placeholder"):
        build_catalog_candidate_provider(
            "deepseek",
            "balanced",
            environment={"DEEPSEEK_API_KEY": "test"},
        )
    with pytest.raises(ValueError, match="non-placeholder"):
        build_catalog_candidate_provider(
            "kimi",
            "max",
            environment={"KIMI_API_KEY": "dummy"},
        )
    with pytest.raises(ValueError, match="non-placeholder"):
        build_catalog_candidate_provider(
            "openai",
            "fast",
            environment={"OPENAI_API_KEY": "placeholder"},
        )


def test_coding_membership_surface_cannot_be_used_as_eachat_adapter() -> None:
    coding_profile = ResolvedProviderProfile(
        provider="kimi",
        effort_profile="max",
        capability=KIMI_CODE_K3,
        provider_parameters={"reasoning_effort": "max"},
        routing_reason="test fixture",
    )
    with pytest.raises(ValueError, match="Coding-only"):
        CatalogCandidateProvider(
            profile=coding_profile,
            transport=FakeTransport(),
        )


@pytest.mark.parametrize(
    ("provider_name", "model_id"),
    [("kimi", "kimi-k3"), ("openai", "gpt-5.6-terra")],
)
def test_live_route_selects_injected_kimi_and_openai_without_fallback(
    monkeypatch,
    provider_name: str,
    model_id: str,
) -> None:
    fake = RouteFakeProvider(provider_name, model_id)

    def factory(provider, effort):
        assert provider == provider_name
        assert effort == "balanced"
        return fake

    monkeypatch.setattr(
        graph_application,
        "build_catalog_candidate_provider",
        factory,
    )
    previous = app.state.energy_chat_runtime
    app.state.energy_chat_runtime = EnergyChatApplicationRuntime()
    try:
        response = client.post(
            "/energy-chat/v2/chat/live",
            json={
                "user_message": "Explain the provider selector.",
                "provider_preference": provider_name,
                "effort_profile": "balanced",
                "thread_id": f"thread-{provider_name}-route",
            },
        )
    finally:
        app.state.energy_chat_runtime = previous

    assert response.status_code == 200, response.text
    body = response.json()
    assert fake.calls == 1
    assert body["requested_provider"] == provider_name
    assert body["served_provider"] == provider_name
    assert body["served_model"] == model_id
    assert body["fallback_used"] is False
    assert body["fallback_authorized"] is False
    assert body["provider_metrics_summary"]["provider_call_count"] == 1


def test_direct_kimi_and_openai_fallback_request_is_rejected() -> None:
    for provider_name in ("kimi", "openai"):
        response = client.post(
            "/energy-chat/v2/chat/live",
            json={
                "user_message": "Test explicit fallback rejection.",
                "provider_preference": provider_name,
                "allow_provider_fallback": True,
                "fallback_provider_allowlist": ["deepseek"],
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"]["error"] == "provider_unavailable"
