"""Small provider-neutral signed-session contract for estimator production identity."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class ActorContext:
    subject: str
    tenant_id: str
    roles: tuple[str, ...]

    @property
    def owner_id(self) -> str:
        return f"{self.tenant_id}:{self.subject}"


class SignedSessionCodec:
    """HMAC-SHA256 backend session tokens with explicit tenant and expiry."""

    version = "v1"

    def __init__(self, signing_key: bytes) -> None:
        if len(signing_key) < 32:
            raise ValueError("session signing key must contain at least 32 bytes")
        self._key = signing_key

    def issue(
        self,
        *,
        subject: str,
        tenant_id: str,
        roles: tuple[str, ...],
        expires_at: datetime,
        issued_at: datetime | None = None,
    ) -> str:
        subject = _identity(subject, "subject")
        tenant_id = _identity(tenant_id, "tenant_id")
        normalized_roles = tuple(dict.fromkeys(_identity(role, "role") for role in roles))
        if not normalized_roles:
            raise ValueError("roles must contain at least one role")
        now = issued_at or datetime.now(UTC)
        _require_aware(now, "issued_at")
        _require_aware(expires_at, "expires_at")
        if expires_at <= now:
            raise ValueError("expires_at must be later than issued_at")
        payload = {
            "exp": int(expires_at.timestamp()),
            "iat": int(now.timestamp()),
            "roles": list(normalized_roles),
            "sub": subject,
            "tenant": tenant_id,
        }
        encoded = _b64_encode(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        )
        signing_input = f"{self.version}.{encoded}".encode("ascii")
        signature = hmac.new(self._key, signing_input, hashlib.sha256).digest()
        return f"{self.version}.{encoded}.{_b64_encode(signature)}"

    def verify(self, token: str, *, now: datetime | None = None) -> ActorContext:
        parts = token.split(".")
        if len(parts) != 3 or parts[0] != self.version:
            raise ValueError("invalid signed session format")
        version, encoded, encoded_signature = parts
        payload_bytes = _b64_decode(encoded, "payload")
        signature = _b64_decode(encoded_signature, "signature")
        expected = hmac.new(
            self._key,
            f"{version}.{encoded}".encode("ascii"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signed session signature is invalid")
        try:
            payload = json.loads(payload_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("signed session payload is invalid") from exc
        if not isinstance(payload, dict):
            raise ValueError("signed session payload is invalid")
        try:
            issued_at = int(payload["iat"])
            expires_at = int(payload["exp"])
            subject = _identity(str(payload["sub"]), "subject")
            tenant_id = _identity(str(payload["tenant"]), "tenant_id")
            raw_roles = payload["roles"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("signed session claims are invalid") from exc
        if not isinstance(raw_roles, list) or not raw_roles:
            raise ValueError("signed session roles are invalid")
        roles = tuple(dict.fromkeys(_identity(str(role), "role") for role in raw_roles))
        current = now or datetime.now(UTC)
        _require_aware(current, "now")
        current_ts = int(current.timestamp())
        if issued_at > current_ts + 60:
            raise ValueError("signed session was issued in the future")
        if expires_at <= current_ts:
            raise ValueError("signed session expired")
        if expires_at <= issued_at:
            raise ValueError("signed session expiry is invalid")
        return ActorContext(subject=subject, tenant_id=tenant_id, roles=roles)


def _identity(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > 120:
        raise ValueError(f"{field} must contain between 1 and 120 characters")
    if not all(character.isalnum() or character in "-_.:@" for character in normalized):
        raise ValueError(f"{field} contains unsupported characters")
    return normalized


def _require_aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


def _b64_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64_decode(value: str, field: str) -> bytes:
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, UnicodeEncodeError) as exc:
        raise ValueError(f"signed session {field} encoding is invalid") from exc
    if _b64_encode(decoded) != value:
        raise ValueError(f"signed session {field} encoding is non-canonical")
    return decoded
