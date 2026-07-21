"""Tests for the selector API — deterministic, no live provider calls."""

from __future__ import annotations  # noqa: I001

from energy_core.selector_api import SelectRequest, SelectResponse, SelectorAPI


def _api() -> SelectorAPI:
    return SelectorAPI()


# ------------------------------------------------------------------
# List models
# ------------------------------------------------------------------


def test_list_models_returns_all_available() -> None:
    api = _api()
    models = api.list_models()
    assert len(models) >= 9  # 11 curated, some may be unavailable
    model_ids = {m.model_id for m in models}
    assert "deepseek-v4-flash" in model_ids
    assert "k3" in model_ids
    assert "gpt-5.6-sol" in model_ids


def test_list_models_excludes_unavailable() -> None:
    from energy_core.provider_registry import CapabilityRegistry
    caps = CapabilityRegistry()._capabilities
    caps["deepseek-v4-flash"] = caps["deepseek-v4-flash"].model_copy(
        update={"availability_state": "unavailable"}
    )
    api = SelectorAPI(CapabilityRegistry(caps))
    model_ids = {m.model_id for m in api.list_models()}
    assert "deepseek-v4-flash" not in model_ids


# ------------------------------------------------------------------
# Get model detail
# ------------------------------------------------------------------


def test_get_model_returns_detail() -> None:
    api = _api()
    detail = api.get_model("k3")
    assert detail is not None
    assert detail.surface == "kimi_code"
    assert detail.model_family == "kimi-k3"
    assert "max" in detail.reasoning_efforts
    assert "pricing" in detail.model_dump()


def test_get_model_unknown_returns_none() -> None:
    api = _api()
    assert api.get_model("nonexistent") is None


# ------------------------------------------------------------------
# Select
# ------------------------------------------------------------------


def test_select_auto_resolves_deepseek() -> None:
    api = _api()
    resp = api.select(SelectRequest(provider="auto", profile="medium"))
    assert resp.status == "ok"
    assert resp.route is not None
    assert resp.route.provider == "deepseek"


def test_select_explicit_kimi() -> None:
    api = _api()
    resp = api.select(SelectRequest(provider="kimi", profile="max"))
    assert resp.status == "ok"
    assert resp.route is not None
    assert resp.route.model_id == "k3"


def test_select_invalid_profile_returns_error() -> None:
    api = _api()
    resp = api.select(SelectRequest(provider="deepseek", profile="unknown"))
    assert resp.status == "error"
    assert resp.error is not None


def test_select_openai_with_premium_reason() -> None:
    api = _api()
    resp = api.select(SelectRequest(
        provider="openai", profile="max", premium_reason="explicit escalation"
    ))
    assert resp.status == "ok"
    assert resp.route is not None
    assert resp.route.model_id == "gpt-5.6-sol"


def test_select_returns_available_models() -> None:
    api = _api()
    resp = api.select(SelectRequest())
    assert len(resp.available_models) > 0


# ------------------------------------------------------------------
# Serialization
# ------------------------------------------------------------------


def test_select_request_round_trips() -> None:
    req = SelectRequest(provider="kimi", profile="max", premium_reason="test")
    dumped = req.model_dump(mode="json")
    reloaded = SelectRequest.model_validate(dumped)
    assert reloaded.provider == "kimi"


def test_select_response_round_trips() -> None:
    resp = SelectResponse(status="ok", error=None)
    dumped = resp.model_dump(mode="json")
    reloaded = SelectResponse.model_validate(dumped)
    assert reloaded.status == "ok"
