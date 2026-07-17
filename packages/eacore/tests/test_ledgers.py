from pathlib import Path

import pytest

from eacore.adapters import InMemoryLedger, JsonlLedger
from eacore.contracts import ConflictingIdentifierError, IntegrityError
from eacore.engine import ledger_record_hash, recover_jsonl


def test_in_memory_replay_is_idempotent(ledger_record) -> None:
    ledger = InMemoryLedger()
    assert ledger.append(ledger_record) is True
    assert ledger.append(ledger_record) is False
    assert ledger.read_all() == (ledger_record,)


def test_in_memory_conflicting_id_fails_closed(ledger_record) -> None:
    ledger = InMemoryLedger()
    ledger.append(ledger_record)
    changed = ledger_record.model_copy(
        update={"decision": ledger_record.decision.model_copy(update={"reason_summary": "changed"})}
    )
    changed = changed.model_copy(update={"canonical_hash": ledger_record_hash(changed)})
    with pytest.raises(ConflictingIdentifierError):
        ledger.append(changed)


def test_jsonl_append_and_read(tmp_path: Path, ledger_record) -> None:
    ledger = JsonlLedger(tmp_path / "ledger.jsonl")
    assert ledger.append(ledger_record) is True
    assert ledger.append(ledger_record) is False
    assert ledger.read_all() == (ledger_record,)


def test_corrupted_line_produces_recovery_report(tmp_path: Path, ledger_record) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = JsonlLedger(path)
    ledger.append(ledger_record)
    path.write_text(path.read_text() + "not-json\n", encoding="utf-8")
    report = recover_jsonl(path)
    assert report.records == (ledger_record,)
    assert len(report.issues) == 1
    assert report.issues[0].line_number == 2
    with pytest.raises(ConflictingIdentifierError):
        ledger.append(ledger_record)


def test_hash_mismatch_is_rejected(ledger_record) -> None:
    bad = ledger_record.model_copy(update={"canonical_hash": "0" * 64})
    with pytest.raises(IntegrityError):
        InMemoryLedger().append(bad)
