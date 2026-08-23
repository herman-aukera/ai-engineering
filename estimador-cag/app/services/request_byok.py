"""Request-scoped bring-your-own-key routing for Energy-Aware model calls.

BYOK credentials exist only in ContextVars for the lifetime of one HTTP request.
They are never checkpointed, logged, stored in application state, or accepted as
arbitrary provider base URLs. When BYOK is active it is exclusive: missing role
credentials fail closed instead of falling back to service-funded credentials.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Literal, Mapping

import litellm

from app.config import TierName, settings
from app.services.litellm_provider import (
    LiteLLMProvider,
    ResolvedModel,
    _litellm_model_name,
)

BYOK_HEADER_NAMES = (
    "X-EA-Worker-Provider",
    "X-EA-Worker-Model",
    "X-EA-Worker-Api-Key",
    "X-EA-Worker-Max-Calls",
    "X-EA-Critic-Provider",
    "X-EA-Critic-Model",
    "X-EA-Critic-Api-Key",
    "X-EA-Critic-Max-Calls",
)
Role = Literal["worker", "critic"]
_ALLOWED_PROVIDERS = frozenset({"deepseek", "kimi", "openai"})
_ROLE_BY_TIER: dict[TierName, Role] = {
    "flash": "worker",
    "backup": "worker",
    "pro": "critic",
    "backup_pro": "critic",
}


class BYOKRequestError(ValueError):
    """Raised when request-scoped BYOK configuration is malformed."""


class BYOKCredentialRequiredError(RuntimeError):
    """Raised instead of silently spending a service-owned provider credential."""


class BYOKBudgetExceededError(RuntimeError):
    """Raised before a provider call would exceed the request-scoped call budget."""


@dataclass(frozen=True)
class BYOKCredential:
    """One request-local provider credential with an allow-listed destination."""

    provider: str
    model: str
    api_key: str = field(repr=False)

    @property
    def base_url(self) -> str:
        return {
            "deepseek": settings.deepseek_base_url,
            "kimi": settings.kimi_base_url,
            "openai": settings.openai_base_url,
        }[self.provider]


@dataclass
class RequestBYOK:
    """Exclusive per-request worker/critic credentials and hard call budgets."""

    worker: BYOKCredential | None = None
    critic: BYOKCredential | None = None
    worker_max_calls: int = 12
    critic_max_calls: int = 4
    worker_calls: int = 0
    critic_calls: int = 0

    @property
    def active(self) -> bool:
        return self.worker is not None or self.critic is not None

    def credential_for_role(self, role: Role) -> BYOKCredential | None:
        return self.worker if role == "worker" else self.critic

    def credential_for_tier(self, tier: TierName) -> BYOKCredential | None:
        return self.credential_for_role(_ROLE_BY_TIER[tier])

    def consume_role(self, role: Role) -> None:
        if role == "worker":
            if self.worker_calls >= self.worker_max_calls:
                raise BYOKBudgetExceededError("BYOK worker model-call budget exhausted")
            self.worker_calls += 1
            return
        if self.critic_calls >= self.critic_max_calls:
            raise BYOKBudgetExceededError("BYOK critic model-call budget exhausted")
        self.critic_calls += 1


_BYOK_CONTEXT: ContextVar[RequestBYOK | None] = ContextVar(
    "energy_aware_request_byok",
    default=None,
)
_BYOK_ACTIVE_ROLE: ContextVar[Role | None] = ContextVar(
    "energy_aware_request_byok_role",
    default=None,
)
_ORIGINAL_RESOLVE_MODEL = LiteLLMProvider.resolve_model
_ORIGINAL_LITELLM_COMPLETION = litellm.completion
_BYOK_PATCH_INSTALLED = False


def _header(headers: Mapping[str, str], name: str) -> str:
    direct = headers.get(name)
    if direct is not None:
        return direct.strip()
    lower = name.casefold()
    for key, value in headers.items():
        if key.casefold() == lower:
            return value.strip()
    return ""


def _positive_budget(raw: str, *, default: int, label: str) -> int:
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise BYOKRequestError(f"{label} must be a positive integer") from exc
    if not 1 <= value <= 100:
        raise BYOKRequestError(f"{label} must be between 1 and 100")
    return value


def _credential(headers: Mapping[str, str], role: Role) -> BYOKCredential | None:
    prefix = "X-EA-Worker" if role == "worker" else "X-EA-Critic"
    provider = _header(headers, f"{prefix}-Provider").casefold()
    model = _header(headers, f"{prefix}-Model")
    api_key = _header(headers, f"{prefix}-Api-Key")
    supplied = [bool(provider), bool(model), bool(api_key)]
    if not any(supplied):
        return None
    if not all(supplied):
        raise BYOKRequestError(
            f"{role} BYOK requires provider, model, and API key together"
        )
    if provider not in _ALLOWED_PROVIDERS:
        raise BYOKRequestError(f"Unsupported {role} BYOK provider")
    if not 1 <= len(model) <= 200:
        raise BYOKRequestError(f"Invalid {role} BYOK model")
    if not 8 <= len(api_key) <= 1000:
        raise BYOKRequestError(f"Invalid {role} BYOK API key")
    return BYOKCredential(provider=provider, model=model, api_key=api_key)


def parse_byok_headers(headers: Mapping[str, str]) -> RequestBYOK | None:
    """Parse allow-listed BYOK headers without retaining the source mapping."""

    worker = _credential(headers, "worker")
    critic = _credential(headers, "critic")
    if worker is None and critic is None:
        return None
    return RequestBYOK(
        worker=worker,
        critic=critic,
        worker_max_calls=_positive_budget(
            _header(headers, "X-EA-Worker-Max-Calls"),
            default=12,
            label="worker max calls",
        ),
        critic_max_calls=_positive_budget(
            _header(headers, "X-EA-Critic-Max-Calls"),
            default=4,
            label="critic max calls",
        ),
    )


def set_request_byok(value: RequestBYOK | None) -> Token[RequestBYOK | None]:
    """Bind BYOK to the current request context."""

    return _BYOK_CONTEXT.set(value)


def reset_request_byok(token: Token[RequestBYOK | None]) -> None:
    """Erase the current request binding even when downstream code fails."""

    _BYOK_CONTEXT.reset(token)
    _BYOK_ACTIVE_ROLE.set(None)


def current_request_byok() -> RequestBYOK | None:
    return _BYOK_CONTEXT.get()


def _resolved_byok_model(tier: TierName, credential: BYOKCredential) -> ResolvedModel:
    role = _ROLE_BY_TIER[tier]
    return ResolvedModel(
        tier=tier,
        provider=credential.provider,
        model=_litellm_model_name(
            provider=credential.provider,
            model=credential.model,
        ),
        api_key=credential.api_key,
        base_url=credential.base_url,
        temperature=0.3 if role == "worker" else 0.2,
    )


def install_byok_provider_override() -> None:
    """Install process-wide hooks whose behavior is activated only by ContextVar.

    The resolve hook selects request-local credentials and refuses service-key
    fallback. The completion hook consumes the budget immediately before every
    real LiteLLM call, including structured-output repair calls.
    """

    global _BYOK_PATCH_INSTALLED
    if _BYOK_PATCH_INSTALLED:
        return

    def resolve_model(provider: LiteLLMProvider, tier: TierName) -> ResolvedModel:
        request_byok = current_request_byok()
        if request_byok is None:
            return _ORIGINAL_RESOLVE_MODEL(provider, tier)
        role = _ROLE_BY_TIER[tier]
        credential = request_byok.credential_for_role(role)
        if credential is None:
            raise BYOKCredentialRequiredError(
                f"BYOK request has no {role} credential for tier {tier}"
            )
        _BYOK_ACTIVE_ROLE.set(role)
        return _resolved_byok_model(tier, credential)

    def completion(*args, **kwargs):
        request_byok = current_request_byok()
        if request_byok is not None:
            role = _BYOK_ACTIVE_ROLE.get()
            if role is None:
                raise BYOKCredentialRequiredError(
                    "BYOK model call was attempted without a resolved request role"
                )
            request_byok.consume_role(role)
        return _ORIGINAL_LITELLM_COMPLETION(*args, **kwargs)

    LiteLLMProvider.resolve_model = resolve_model
    litellm.completion = completion
    _BYOK_PATCH_INSTALLED = True


__all__ = [
    "BYOKBudgetExceededError",
    "BYOKCredential",
    "BYOKCredentialRequiredError",
    "BYOK_HEADER_NAMES",
    "BYOKRequestError",
    "RequestBYOK",
    "current_request_byok",
    "install_byok_provider_override",
    "parse_byok_headers",
    "reset_request_byok",
    "set_request_byok",
]
