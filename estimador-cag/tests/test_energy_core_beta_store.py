import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from energy_core.beta_demo import BetaDemoRunner
from energy_core.beta_store import SQLiteBetaDemoStore
from energy_core.coding_agent import CodingProposal

OWNER = "owner-1"


def _prepared(proposal_id: str):
    proposal = CodingProposal(
        proposal_id=proposal_id,
        objective="Persist a safe proposal.",
        spec_id="0012-production-hardening",
        patch="def status():\n    return 'ok'\n",
        changed_files=("app/status.py",),
        proposed_commands=(("git", "status", "--short"),),
    )
    return BetaDemoRunner().prepare(proposal)


def test_result_survives_store_recreation_and_receipt_is_one_time(tmp_path) -> None:
    database = tmp_path / "eacode.sqlite3"
    store = SQLiteBetaDemoStore(database)
    prepared = _prepared("persistent-1")
    store.create_result(prepared, owner_id=OWNER)

    restarted = SQLiteBetaDemoStore(database)
    loaded = restarted.get_result("persistent-1", owner_id=OWNER)
    assert loaded == prepared

    scope = BetaDemoRunner().authorization_scope(loaded)
    receipt = restarted.issue_authorization(
        proposal_id="persistent-1",
        actor=OWNER,
        owner_id=OWNER,
        scope=scope,
    )
    consumed = restarted.consume_authorization(
        receipt_id=receipt.receipt_id,
        proposal_id="persistent-1",
        actor=OWNER,
        owner_id=OWNER,
        scope=scope,
    )
    assert consumed.consumed_at is not None

    with pytest.raises(PermissionError, match="already_consumed"):
        restarted.consume_authorization(
            receipt_id=receipt.receipt_id,
            proposal_id="persistent-1",
            actor=OWNER,
            owner_id=OWNER,
            scope=scope,
        )


def test_result_is_tenant_scoped_but_admin_filter_can_read(tmp_path) -> None:
    store = SQLiteBetaDemoStore(tmp_path / "eacode.sqlite3")
    prepared = _prepared("tenant-1")
    store.create_result(prepared, owner_id=OWNER)

    assert store.get_result("tenant-1", owner_id="other-owner") is None
    assert store.get_result("tenant-1", owner_id=None) == prepared


def test_receipt_is_bound_to_actor_and_exact_scope(tmp_path) -> None:
    store = SQLiteBetaDemoStore(tmp_path / "eacode.sqlite3")
    prepared = _prepared("persistent-2")
    store.create_result(prepared, owner_id=OWNER)
    scope = BetaDemoRunner().authorization_scope(prepared)
    receipt = store.issue_authorization(
        proposal_id="persistent-2",
        actor=OWNER,
        owner_id=OWNER,
        scope=scope,
    )

    with pytest.raises(PermissionError, match="actor_mismatch"):
        store.consume_authorization(
            receipt_id=receipt.receipt_id,
            proposal_id="persistent-2",
            actor="operator-2",
            owner_id=OWNER,
            scope=scope,
        )
    with pytest.raises(PermissionError, match="scope_mismatch"):
        store.consume_authorization(
            receipt_id=receipt.receipt_id,
            proposal_id="persistent-2",
            actor=OWNER,
            owner_id=OWNER,
            scope=(("pytest", "-q"),),
        )


def test_only_one_execution_can_be_reserved_across_multiple_receipts(tmp_path) -> None:
    store = SQLiteBetaDemoStore(tmp_path / "eacode.sqlite3")
    prepared = _prepared("persistent-race")
    store.create_result(prepared, owner_id=OWNER)
    scope = BetaDemoRunner().authorization_scope(prepared)
    first = store.issue_authorization(
        proposal_id="persistent-race",
        actor=OWNER,
        owner_id=OWNER,
        scope=scope,
    )
    second = store.issue_authorization(
        proposal_id="persistent-race",
        actor=OWNER,
        owner_id=OWNER,
        scope=scope,
    )

    store.consume_authorization(
        receipt_id=first.receipt_id,
        proposal_id="persistent-race",
        actor=OWNER,
        owner_id=OWNER,
        scope=scope,
    )
    with pytest.raises(PermissionError, match="execution_already_reserved"):
        store.consume_authorization(
            receipt_id=second.receipt_id,
            proposal_id="persistent-race",
            actor=OWNER,
            owner_id=OWNER,
            scope=scope,
        )


def test_expired_receipt_fails_closed(tmp_path) -> None:
    store = SQLiteBetaDemoStore(tmp_path / "eacode.sqlite3")
    prepared = _prepared("persistent-3")
    store.create_result(prepared, owner_id=OWNER)
    scope = BetaDemoRunner().authorization_scope(prepared)
    now = datetime(2026, 8, 5, 18, 0, tzinfo=UTC)
    receipt = store.issue_authorization(
        proposal_id="persistent-3",
        actor=OWNER,
        owner_id=OWNER,
        scope=scope,
        now=now,
        ttl_seconds=1,
    )

    with pytest.raises(PermissionError, match="receipt_expired"):
        store.consume_authorization(
            receipt_id=receipt.receipt_id,
            proposal_id="persistent-3",
            actor=OWNER,
            owner_id=OWNER,
            scope=scope,
            now=now + timedelta(seconds=2),
        )


def test_persisted_result_tampering_is_detected(tmp_path) -> None:
    database = tmp_path / "eacode.sqlite3"
    store = SQLiteBetaDemoStore(database)
    store.create_result(_prepared("persistent-4"), owner_id=OWNER)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE beta_demo_runs SET result_json = ? WHERE proposal_id = ?",
            ("{}", "persistent-4"),
        )
        connection.commit()

    with pytest.raises(PermissionError, match="integrity"):
        store.get_result("persistent-4", owner_id=OWNER)
