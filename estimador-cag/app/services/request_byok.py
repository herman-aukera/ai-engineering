"""Request-scoped BYOK routing for human product testing.

Credentials live only in a ContextVar for the lifetime of one HTTP request. They
are never written to graph state, PostgreSQL, logs, URLs, cookies, or browser
storage. The server keeps provider base URLs allowlisted to avoid turning BYOK
into an arbitrary outbound-request primitive.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Literal, Mapping

from app.config import TierName, settings
from app.services.litellm_provider import LiteLLMProvider, ResolvedModel, _litellm_model_name

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
_ALLOWED_PROVIDERS = {"deepseek", "kimi", "openai"}
_ROLE_BY_TIER: dict[TierName, Role] = {
    "flash": "worker",
    "backup": "worker",
    "pro": "critic",
    "backup_pro": "critic",
}


@dataclass(frozen=True)
class BYOKCredential:
    provider: str
    model: str
    api_key: str

    @property
    def base_url(self) -> str:
        return {
            "deepseek": settings.deepseek_base_url,
            "kimi": settings.kimi_base_url,
            "openai": settings.openai_base_url,
        }[self.provider]


@dataclass
class RequestBYOK:
    worker: BYOKCredential | None = None
    critic: BYOKCredential | None = None
    worker_max_calls: int = 12
    critic_max_calls: int = 4
    worker_calls: int = 0
    critic_calls: int = 0

    def credential_for_tier(self, tier: TierName) -> BYOKCredential | None:
        role = _ROLE_BY_TIER[tier]
        return self.worker if role == "worker" else self.critic

    def consume_for_tier(self, tier: TierName) -> None:
        role = _ROLE_BY_TIER[tier]
        if role == "worker":
            if self.worker is None:
                return
            if self.worker_calls >= self.worker_max_calls:
                raise RuntimeError("BYOK worker call budget exhausted")
            self.worker_calls += 1
            return
        if self.critic is None:
            return
        if self.critic_calls >= self.critic_max_calls:
            raise RuntimeError("BYOK critic call budget exhausted")
        self.critic_calls += 1


_BYOK_CONTEXT: ContextVar[RequestBYOK | None] = ContextVar("energy_aware_byok", default=None)
_ORIGINAL_RESOLVE_MODEL = LiteLLMProvider.resolve_model
_BYOK_PATCH_INSTALLED = False


def _parse_positive_int(raw: str | None, *, default: int, maximum: int, label: str) -> int:
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{label} must be an integer") from exc
    if not 1 <= value <= maximum:
        raise ValueError(f"{label} must be between 1 and {maximum}")
    return value


def _credential(headers: Mapping[str, str], role: Role) -> BYOKCredential | None:
    prefix = "X-EA-Worker" if role == "worker" else "X-EA-Critic"
    provider = (headers.get(f"{prefix}-Provider") or "").strip().lower()
    model = (headers.get(f"{prefix}-Model") or "").strip()
    api_key = (headers.get(f"{prefix}-Api-Key") or "").strip()
    supplied = (bool(provider), bool(model), bool(api_key))
    if not any(supplied):
        return None
    if not all(supplied):
        raise ValueError(f"{role} BYOK requires provider, model, and API key together")
    if provider not in _ALLOWED_PROVIDERS:
        raise ValueError(f"unsupported {role} BYOK provider: {provider}")
    if len(model) > 200:
        raise ValueError(f"{role} BYOK model is too long")
    if len(api_key) < 8 or len(api_key) > 1000:
        raise ValueError(f"{role} BYOK API key has an invalid length")
    return BYOKCredential(provider=provider, model=model, api_key=api_key)


def parse_byok_headers(headers: Mapping[str, str]) -> RequestBYOK | None:
    """Parse all-or-nothing role credentials without returning secret-bearing errors."""

    worker = _credential(headers, "worker")
    critic = _credential(headers, "critic")
    if worker is None and critic is None:
        return None
    return RequestBYOK(
        worker=worker,
        critic=critic,
        worker_max_calls=_parse_positive_int(
            headers.get("X-EA-Worker-Max-Calls"), default=12, maximum=30, label="worker max calls"
        ),
        critic_max_calls=_parse_positive_int(
            headers.get("X-EA-Critic-Max-Calls"), default=4, maximum=10, label="critic max calls"
        ),
    )


def set_request_byok(config: RequestBYOK | None) -> Token[RequestBYOK | None]:
    return _BYOK_CONTEXT.set(config)


def reset_request_byok(token: Token[RequestBYOK | None]) -> None:
    _BYOK_CONTEXT.reset(token)


def current_request_byok() -> RequestBYOK | None:
    return _BYOK_CONTEXT.get()


def install_byok_provider_override() -> None:
    """Make existing LiteLLMProvider instances honor request-local role credentials."""

    global _BYOK_PATCH_INSTALLED
    if _BYOK_PATCH_INSTALLED:
        return

    def resolve_model(self: LiteLLMProvider, tier: TierName) -> ResolvedModel:
        request_byok = current_request_byok()
        if request_byok is not None:
            credential = request_byok.credential_for_tier(tier)
            if credential is not None:
                request_byok.consume_for_tier(tier)
                return ResolvedModel(
                    tier=tier,
                    provider=credential.provider,
                    model=_litellm_model_name(provider=credential.provider, model=credential.model),
                    api_key=credential.api_key,
                    base_url=credential.base_url,
                    temperature=0.3 if _ROLE_BY_TIER[tier] == "worker" else 0.2,
                )
        return _ORIGINAL_RESOLVE_MODEL(self, tier)

    LiteLLMProvider.resolve_model = resolve_model
    _BYOK_PATCH_INSTALLED = True


__all__ = [
    "BYOKCredential",
    "BYOK_HEADER_NAMES",
    "RequestBYOK",
    "current_request_byok",
    "install_byok_provider_override",
    "parse_byok_headers",
    "reset_request_byok",
    "set_request_byok",
]
