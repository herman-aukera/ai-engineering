from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import Field, field_validator

from .base import StrictModel


class TrustClass(StrEnum):
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"
    UNKNOWN = "unknown"


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FAILED = "failed"


class Sensitivity(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE_REFERENCE = "sensitive_reference"


class RedactionStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    REDACTED = "redacted"
    REFERENCE_ONLY = "reference_only"


class EvidenceRef(StrictModel):
    evidence_id: str
    evidence_kind: str
    source_ref: str
    producer: str
    recorded_at: datetime
    content_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    hash_algorithm: str | None = Field(default=None, pattern=r"^sha256$")
    trust_classification: TrustClass
    verification_status: VerificationStatus
    sensitivity: Sensitivity
    redaction_status: RedactionStatus
    fresh_until: datetime | None = None

    @field_validator("recorded_at", "fresh_until")
    @classmethod
    def normalize_time(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evidence timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)
