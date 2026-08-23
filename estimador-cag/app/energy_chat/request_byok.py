"""Request-local BYOK credentials for Energy Aware Chat live model calls.

Credentials are held only in ContextVars for one HTTP request. Provider targets
remain constrained by the verified EACHAT catalog. A BYOK request is exclusive:
missing role credentials fail closed instead of using service-funded credentials.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Literal

from app.energy_chat.provider_catalog import EffortProfile, ProviderName

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


class BYOKRequestError(ValueError):
    """Raised when BYOK request headers do not form a safe complete contract."""


class BYOKCredentialRequiredError(RuntimeError):
    """Raised instead of falling back to a service-owned credential."""


class BYOKBudgetExceededError(RuntimeError):
    """Raised immediately before a model call would exceed its role budget."""


@dataclass(frozen=True)
class BYOKCredential:
    provider: ProviderName
    model: str
    api_key: str = field(repr=False)


@dataclass
class RequestBYOK:
    worker: BYOKCredential | None = None
    critic: BYOKCredential | None = None
    worker_max_calls: int = 12
    critic_max_calls: int = 4
    worker_calls: int = 0
    critic_calls: int = 0

    def role_for_effort(self, effort: EffortProfile) -> Role:
        return "worker" if effort == "fast" else "critic"

    def credential_for_effort(self, effort: EffortProfile) -> BYOKCredential:
        role = self.role_for_effort(effort)
        credential = self.worker if role == "worker" else self.critic
        if credential is None:
            raise BYOKCredentialRequiredError(
                f"BYOK request has no {role} credential for effort {effort}"
            )
        return credential

    def consume_effort(self, effort: EffortProfile) -> None:
        role = self.role_for_effort(effort)
        if role == "worker":
            if self.worker_calls >= self.worker_max_calls:
                raise BYOKBudgetExceededError("BYOK worker model-call budget exhausted")
            self.worker_calls += 1
            return
        if self.critic_calls >= self.critic_max_calls:
            raise BYOKBudgetExceededError("BYOK critic model-call budget exhausted")
        self.critic_calls += 1


_CONTEXT: ContextVar[RequestBYOK | None] = ContextVar("eachat_request_byok", default=None)


def _header(headers: Mapping[str, str], name: str) -> str:
    direct = headers.get(name)
    if direct is not None:
        return direct.strip()
    folded = name.casefold()
    for key, value in headers.items():
        if key.casefold() == folded:
            return value.strip()
    return ""


def _budget(raw: str, *, default: int, label: str) -> int:
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
    supplied = (bool(provider), bool(model), bool(api_key))
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
    return BYOKCredential(
        provider=provider,  # type: ignore[arg-type]
        model=model,
        api_key=api_key,
    )


def parse_byok_headers(headers: Mapping[str, str]) -> RequestBYOK | None:
    worker = _credential(headers, "worker")
    critic = _credential(headers, "critic")
    if worker is None and critic is None:
        return None
    return RequestBYOK(
        worker=worker,
        critic=critic,
        worker_max_calls=_budget(
            _header(headers, "X-EA-Worker-Max-Calls"),
            default=12,
            label="worker max calls",
        ),
        critic_max_calls=_budget(
            _header(headers, "X-EA-Critic-Max-Calls"),
            default=4,
            label="critic max calls",
        ),
    )


def set_request_byok(value: RequestBYOK | None) -> Token[RequestBYOK | None]:
    return _CONTEXT.set(value)


def reset_request_byok(token: Token[RequestBYOK | None]) -> None:
    _CONTEXT.reset(token)


def current_request_byok() -> RequestBYOK | None:
    return _CONTEXT.get()


__all__ = [
    "BYOKBudgetExceededError",
    "BYOKCredential",
    "BYOKCredentialRequiredError",
    "BYOK_HEADER_NAMES",
    "BYOKRequestError",
    "RequestBYOK",
    "current_request_byok",
    "parse_byok_headers",
    "reset_request_byok",
    "set_request_byok",
]
