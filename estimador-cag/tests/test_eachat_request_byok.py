from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.energy_chat.byok_provider_override as override
from app.energy_chat.api_v2_contracts import EnergyChatV2Request, ProviderUnavailableError
from app.energy_chat.byok_provider_override import install_byok_provider_override
from app.energy_chat.provider_adapters import ProviderTransportResult
from app.energy_chat.request_byok import (
    BYOKBudgetExceededError,
    BYOKCredential,
    BYOKCredentialRequiredError,
    BYOKRequestError,
    RequestBYOK,
    parse_byok_headers,
    reset_request_byok,
    set_request_byok,
)


class FakeTransport:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, *, profile, messages, max_output_tokens):
        del profile, messages, max_output_tokens
        self.calls += 1
        return ProviderTransportResult(answer="grounded answer")


def test_eachat_byok_contract_redacts_secret_and_requires_complete_role() -> None:
    with pytest.raises(BYOKRequestError):
        parse_byok_headers({"X-EA-Critic-Api-Key": "critic-secret-key"})

    request_byok = parse_byok_headers(
        {
            "X-EA-Worker-Provider": "deepseek",
            "X-EA-Worker-Model": "deepseek-v4-flash",
            "X-EA-Worker-Api-Key": "worker-secret-key",
            "X-EA-Critic-Provider": "openai",
            "X-EA-Critic-Model": "gpt-5.6-terra",
            "X-EA-Critic-Api-Key": "critic-secret-key",
        }
    )
    assert request_byok is not None
    rendered = repr(request_byok)
    assert "worker-secret-key" not in rendered
    assert "critic-secret-key" not in rendered


def test_eachat_byok_role_selection_is_fail_closed() -> None:
    request_byok = RequestBYOK(
        worker=BYOKCredential(
            provider="deepseek",
            model="deepseek-v4-flash",
            api_key="worker-secret-key",
        )
    )
    assert request_byok.credential_for_effort("fast").provider == "deepseek"
    with pytest.raises(BYOKCredentialRequiredError):
        request_byok.credential_for_effort("balanced")


def test_eachat_budget_is_charged_immediately_before_transport_call() -> None:
    fake = FakeTransport()
    request_byok = RequestBYOK(
        worker=BYOKCredential(
            provider="deepseek",
            model="deepseek-v4-flash",
            api_key="worker-secret-key",
        ),
        worker_max_calls=1,
    )
    token = set_request_byok(request_byok)
    try:
        transport = override._BudgetedTransport(fake, "fast")
        result = transport.complete(
            profile=SimpleNamespace(),
            messages=[{"role": "user", "content": "hello"}],
            max_output_tokens=64,
        )
        assert result.answer == "grounded answer"
        with pytest.raises(BYOKBudgetExceededError):
            transport.complete(
                profile=SimpleNamespace(),
                messages=[{"role": "user", "content": "again"}],
                max_output_tokens=64,
            )
        assert fake.calls == 1
    finally:
        reset_request_byok(token)


def test_eachat_byok_uses_verified_catalog_model_and_ignores_request_provider() -> None:
    install_byok_provider_override()
    request_byok = RequestBYOK(
        critic=BYOKCredential(
            provider="openai",
            model="gpt-5.6-terra",
            api_key="critic-secret-key",
        )
    )
    token = set_request_byok(request_byok)
    try:
        request = EnergyChatV2Request(
            user_message="Use the supplied project evidence to answer this question.",
            provider_preference="deepseek",
            effort_profile="balanced",
            execution_profile="live_bounded",
        )
        provider = override.graph_application._resolve_provider(request, "live_bounded")
        assert provider.profile.provider == "openai"
        assert provider.profile.capability.model_id == "gpt-5.6-terra"
    finally:
        reset_request_byok(token)


def test_eachat_byok_rejects_uncatalogued_model_and_fallback() -> None:
    install_byok_provider_override()
    request_byok = RequestBYOK(
        critic=BYOKCredential(
            provider="openai",
            model="unverified-model",
            api_key="critic-secret-key",
        )
    )
    token = set_request_byok(request_byok)
    try:
        request = EnergyChatV2Request(
            user_message="Answer this project question with bounded live inference.",
            effort_profile="balanced",
            execution_profile="live_bounded",
        )
        with pytest.raises(ProviderUnavailableError):
            override.graph_application._resolve_provider(request, "live_bounded")
    finally:
        reset_request_byok(token)
