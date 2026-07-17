from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from .base import StrictModel


class CriticSeverity(StrEnum):
    INFO = "info"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class CriticFindingEnvelope(StrictModel):
    finding_id: str
    critic_id: str
    critic_version: str
    constraint_id: str
    severity: CriticSeverity
    status: str
    affected_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    repair_ref: str | None = None
    summary: str = Field(min_length=1, max_length=2000)
    deterministic: bool
