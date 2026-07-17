from __future__ import annotations

from eacore.contracts import ConflictingIdentifierError, LedgerRecord
from eacore.engine.integrity import verify_ledger_record


class InMemoryLedger:
    def __init__(self) -> None:
        self._records: list[LedgerRecord] = []
        self._by_id: dict[str, LedgerRecord] = {}

    def append(self, record: LedgerRecord) -> bool:
        verify_ledger_record(record)
        record_id = record.identity.record_id
        existing = self._by_id.get(record_id)
        if existing is not None:
            if existing == record:
                return False
            raise ConflictingIdentifierError(
                f"ledger id {record_id} reused with different content"
            )
        self._by_id[record_id] = record
        self._records.append(record)
        return True

    def read_all(self) -> tuple[LedgerRecord, ...]:
        return tuple(self._records)
