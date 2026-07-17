from __future__ import annotations

from pathlib import Path

from eacore.contracts import ConflictingIdentifierError, LedgerRecord
from eacore.engine.canonical import canonical_json
from eacore.engine.integrity import recover_jsonl, verify_ledger_record


class JsonlLedger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, record: LedgerRecord) -> bool:
        verify_ledger_record(record)
        report = recover_jsonl(self.path)
        if report.issues:
            raise ConflictingIdentifierError("ledger is corrupted; recover before append")
        for existing in report.records:
            if existing.identity.record_id == record.identity.record_id:
                if existing == record:
                    return False
                raise ConflictingIdentifierError(
                    f"ledger id {record.identity.record_id} reused with different content"
                )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical_json(record) + "\n")
        return True

    def read_all(self) -> tuple[LedgerRecord, ...]:
        report = recover_jsonl(self.path)
        if report.issues:
            raise ConflictingIdentifierError("ledger contains corrupted rows")
        return report.records
