from __future__ import annotations

from pydantic import Field

from .base import StrictModel
from .decisions import DecisionEnvelope
from .identity import RecordIdentity
from .retention import RetentionClass
from .versions import VersionIdentity


class LedgerRecord(StrictModel):
    identity: RecordIdentity
    version: VersionIdentity
    decision: DecisionEnvelope
    canonical_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    previous_record_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    retention_class: RetentionClass
