"""Production BYOK adapter for the existing EACHAT provider-neutral graph seam."""

from __future__ import annotations

from typing import Any

import app.energy_chat.graph_application as graph_application
from app.energy_chat.api_v2_contracts import EnergyChatV2Request, ProviderUnavailableError
from app.energy_chat.candidate_provider import CandidateProvider
from app.energy_chat.provider_adapters import (
    CatalogCandidateProvider,
    OpenAICompatibleChatTransport,
    OpenAIResponsesTransport,
    ProviderTransport,
    ProviderTransportResult,
)
from app.energy_chat.provider_catalog import EffortProfile, resolve_effort_profile
from app.energy_chat.request_byok import current_request_byok

_ORIGINAL_RESOLVE_PROVIDER = graph_application._resolve_provider
_PATCH_INSTALLED = False


class _BudgetedTransport:
    """Consume the role budget immediately before each external provider call."""

    def __init__(self, delegate: ProviderTransport, effort: EffortProfile) -> None:
        self._delegate = delegate
        self._effort = effort

    def complete(
        self,
        *,
        profile,
        messages: list[dict[str, str]],
        max_output_tokens: int,
    ) -> ProviderTransportResult:
        request_byok = current_request_byok()
        if request_byok is None:
            raise RuntimeError("BYOK transport escaped its request context")
        request_byok.consume_effort(self._effort)
        return self._delegate.complete(
            profile=profile,
            messages=messages,
            max_output_tokens=max_output_tokens,
        )


def _byok_provider(request: EnergyChatV2Request) -> CandidateProvider:
    request_byok = current_request_byok()
    if request_byok is None:
        raise RuntimeError("BYOK provider requested without request context")
    if request.allow_provider_fallback:
        raise ProviderUnavailableError(
            provider="byok",
            detail=(
                "BYOK requests use explicit role credentials and do not permit "
                "service-funded provider fallback."
            ),
        )
    credential = request_byok.credential_for_effort(request.effort_profile)
    profile = resolve_effort_profile(credential.provider, request.effort_profile)
    if profile is None:
        raise ProviderUnavailableError(
            provider=credential.provider,
            detail="No verified EACHAT profile exists for this BYOK provider/effort.",
        )
    expected_model = profile.capability.model_id
    if credential.model != expected_model:
        raise ProviderUnavailableError(
            provider=credential.provider,
            detail=(
                "BYOK model must match the verified EACHAT catalog model for the "
                f"selected role/effort: {expected_model}."
            ),
        )
    if credential.provider in {"deepseek", "kimi"}:
        delegate: ProviderTransport = OpenAICompatibleChatTransport(
            api_key=credential.api_key,
            base_url=profile.capability.endpoint_base_url,
        )
    elif credential.provider == "openai":
        delegate = OpenAIResponsesTransport(api_key=credential.api_key)
    else:  # pragma: no cover - constrained by the parsed BYOK contract
        raise ProviderUnavailableError(
            provider=str(credential.provider),
            detail="Unsupported BYOK provider.",
        )
    return CatalogCandidateProvider(
        profile=profile,
        transport=_BudgetedTransport(delegate, request.effort_profile),
    )


def install_byok_provider_override() -> None:
    """Make live_bounded graph resolution BYOK-aware without changing graph policy."""

    global _PATCH_INSTALLED
    if _PATCH_INSTALLED:
        return

    def resolve_provider(request: EnergyChatV2Request, execution_profile: str) -> Any:
        if current_request_byok() is None or execution_profile != "live_bounded":
            return _ORIGINAL_RESOLVE_PROVIDER(request, execution_profile)  # type: ignore[arg-type]
        return _byok_provider(request)

    graph_application._resolve_provider = resolve_provider
    _PATCH_INSTALLED = True


__all__ = ["install_byok_provider_override"]
