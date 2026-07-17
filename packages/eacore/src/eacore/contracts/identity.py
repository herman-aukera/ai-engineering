from __future__ import annotations

from datetime import datetime, timezone
import re

from pydantic import field_validator

from .base import StrictModel

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class RecordIdentity(StrictModel):
    record_id: str
    run_id: str
    product: str
    recorded_at: datetime
    producer: str

    @field_validator("record_id", "run_id", "product", "producer")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not _ID.fullmatch(value):
            raise ValueError("identity values must be stable non-secret identifiers")
        return value

    @field_validator("recorded_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_at must be timezone-aware")
        return value.astimezone(timezone.utc)
