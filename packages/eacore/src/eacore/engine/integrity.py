from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from eacore.contracts import IntegrityError, LedgerRecord

from .hashing import ledger_record_hash


@dataclass(frozen=True)
class RecoveryIssue:
    line_number: int
    reason: str


@dataclass(frozen=True)
class RecoveryReport:
    records: tuple[LedgerRecord, ...]
    issues: tuple[RecoveryIssue, ...]


def recover_jsonl(path: Path) -> RecoveryReport:
    records: list[LedgerRecord] = []
    issues: list[RecoveryIssue] = []
    if not path.exists():
        return RecoveryReport((), ())
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            records.append(LedgerRecord.model_validate(json.loads(raw)))
        except Exception as exc:  # explicit recovery artifact, never silent
            issues.append(RecoveryIssue(line_number, f"{type(exc).__name__}: {exc}"))
    return RecoveryReport(tuple(records), tuple(issues))


def verify_ledger_record(record: LedgerRecord) -> None:
    expected = ledger_record_hash(record)
    if expected != record.canonical_hash:
        raise IntegrityError(
            f"ledger record {record.identity.record_id} hash mismatch: "
            f"expected {expected}, got {record.canonical_hash}"
        )
