from __future__ import annotations

import pytest

import app.services.request_byok as byok_module
from app.services.litellm_provider import LiteLLMProvider
from app.services.request_byok import (
    BYOKBudgetExceededError,
    BYOKCredential,
    BYOKCredentialRequiredError,
    BYOKRequestError,
    RequestBYOK,
    install_byok_provider_override,
    parse_byok_headers,
    reset_request_byok,
    set_request_byok,
)


def test_byok_headers_are_all_or_none_and_secrets_are_redacted() -> None:
    with pytest.raises(BYOKRequestError):
        parse_byok_headers({"X-EA-Worker-Provider": "deepseek"})

    request_byok = parse_byok_headers(
        {
            "X-EA-Worker-Provider": "deepseek",
            "X-EA-Worker-Model": "deepseek-chat",
            "X-EA-Worker-Api-Key": "super-secret-worker-key",
            "X-EA-Worker-Max-Calls": "2",
        }
    )
    assert request_byok is not None
    assert request_byok.worker is not None
    assert request_byok.worker_max_calls == 2
    assert "super-secret-worker-key" not in repr(request_byok)


def test_byok_request_never_falls_back_to_service_owned_role() -> None:
    install_byok_provider_override()
    token = set_request_byok(
        RequestBYOK(
            worker=BYOKCredential(
                provider="deepseek",
                model="deepseek-chat",
                api_key="worker-secret-key",
            )
        )
    )
    try:
        provider = LiteLLMProvider()
        assert provider.resolve_model("flash").api_key == "worker-secret-key"
        with pytest.raises(BYOKCredentialRequiredError):
            provider.resolve_model("pro")
    finally:
        reset_request_byok(token)


def test_byok_budget_is_consumed_by_actual_completion_calls(monkeypatch) -> None:
    install_byok_provider_override()
    calls: list[dict[str, object]] = []

    def fake_completion(*args, **kwargs):
        calls.append(kwargs)
        return {"ok": True}

    monkeypatch.setattr(byok_module, "_ORIGINAL_LITELLM_COMPLETION", fake_completion)
    request_byok = RequestBYOK(
        worker=BYOKCredential(
            provider="deepseek",
            model="deepseek-chat",
            api_key="worker-secret-key",
        ),
        worker_max_calls=1,
    )
    token = set_request_byok(request_byok)
    try:
        provider = LiteLLMProvider()
        resolved = provider.resolve_model("flash")
        assert resolved.api_key == "worker-secret-key"
        assert byok_module.litellm.completion(model=resolved.model) == {"ok": True}
        with pytest.raises(BYOKBudgetExceededError):
            byok_module.litellm.completion(model=resolved.model)
        assert len(calls) == 1
    finally:
        reset_request_byok(token)
