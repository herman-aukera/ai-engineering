from __future__ import annotations

from datetime import datetime, timezone

from pydantic import Field, field_validator

from .base import StrictModel


class TraceEventEnvelope(StrictModel):
    event_id: str
    trace_id: str
    sequence: int = Field(ge=0)
    recorded_at: datetime
    actor: str
    phase: str
    action: str
    candidate_ref: str | None = None
    evidence_refs: tuple[str, ...] = ()
    decision_ref: str | None = None
    state_delta_refs: tuple[str, ...] = ()
    summary: str = Field(min_length=1, max_length=1000)

    @field_validator("recorded_at")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("trace timestamp must be timezone-aware")
        return value.astimezone(timezone.utc)
