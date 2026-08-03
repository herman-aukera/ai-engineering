"""Provider-neutral local identity and deterministic session contracts."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Literal

from pydantic import Field, model_validator

from energy_core.models import EnergyModel

Role = Literal["viewer", "reviewer", "operator", "admin"]
IdentityProvider = Literal["google", "apple"]


class LinkedIdentity(EnergyModel):
    provider: IdentityProvider
    subject: str = Field(min_length=1)


class LocalUser(EnergyModel):
    user_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    roles: tuple[Role, ...] = ("viewer",)
    linked_identities: tuple[LinkedIdentity, ...] = Field(default_factory=tuple)


class IdentityProviderConfig(EnergyModel):
    provider: IdentityProvider
    client_id: str = Field(min_length=1)
    redirect_uri: str = Field(pattern=r"^https?://")
    issuer: str = Field(pattern=r"^https://")
    apple_team_id: str | None = None
    apple_key_id: str | None = None
    apple_service_id: str | None = None
    readiness: Literal["configured_not_live_verified"] = "configured_not_live_verified"

    @model_validator(mode="after")
    def validate_provider_contract(self) -> IdentityProviderConfig:
        if self.provider == "apple" and not all(
            (self.apple_team_id, self.apple_key_id, self.apple_service_id)
        ):
            raise ValueError("Apple configuration requires team, key, and service identifiers.")
        return self


class BackendSession(EnergyModel):
    user_id: str
    roles: tuple[Role, ...]
    issued_at: datetime
    expires_at: datetime


class SessionSigner:
    def __init__(self, key: bytes) -> None:
        if len(key) < 32:
            raise ValueError("Session signing key must contain at least 32 bytes.")
        self._key = key

    def issue(self, *, user_id: str, roles: tuple[Role, ...], expires_at: datetime) -> str:
        session = BackendSession(
            user_id=user_id,
            roles=roles,
            issued_at=datetime.now(UTC),
            expires_at=expires_at,
        )
        payload = session.model_dump_json().encode()
        encoded = self._encode(payload)
        signature = hmac.new(self._key, encoded.encode(), hashlib.sha256).hexdigest()
        return f"{encoded}.{signature}"

    def verify(self, token: str) -> BackendSession:
        try:
            encoded, signature = token.rsplit(".", 1)
        except ValueError as exc:
            raise ValueError("Invalid session token signature.") from exc
        expected = hmac.new(self._key, encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid session token signature.")
        try:
            payload = json.loads(self._decode(encoded))
            session = BackendSession.model_validate(payload)
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid session token payload.") from exc
        if session.expires_at <= datetime.now(UTC):
            raise ValueError("Session token has expired.")
        return session

    @staticmethod
    def _encode(payload: bytes) -> str:
        return base64.urlsafe_b64encode(payload).decode().rstrip("=")

    @staticmethod
    def _decode(value: str) -> bytes:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
