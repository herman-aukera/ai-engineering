"""Persistent one-time live authorization tests for Spec 0009."""

from __future__ import annotations  # noqa: I001

import sqlite3
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from energy_core.controlled_execution import CommandProposal, ExecutionPlan, build_execution_plan
from energy_core.live_authorization import (
    LiveAuthorizationContext,
    LiveAuthorizationRequest,
    LiveAuthorizationReceipt,
    SQLiteLiveAuthorizationStore,
    issue_live_authorization,
    scope_for_live_execution,
)
from energy_core.live_execution_contract import RepositorySnapshot


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.email", "tests@example.invalid")
    _git(root, "config", "user.name", "EACODE Tests")
    (root / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(root, "add", "tracked.txt")
    _git(root, "commit", "-m", "initial")
    return root


def _plan(root: Path, *, executable: str = "pytest") -> ExecutionPlan:
    return build_execution_plan(
        CommandProposal(
            proposal_id="proposal-live-authority-store",
            executable=executable,
            arguments=["-q"],
            working_directory=".",
            requested_mode="fake",
            timeout_seconds=30,
            max_output_chars=1024,
            rollback_summary="Read-only test execution.",
        ),
        repository_root=root,
    )


def _context(**overrides: object) -> LiveAuthorizationContext:
    payload: dict[str, object] = {
        "current_revision": 1,
        "trusted_actors": ["gonzalo"],
        "now": datetime(2026, 7, 21, 18, 5, tzinfo=UTC),
    }
    payload.update(overrides)
    return LiveAuthorizationContext.model_validate(payload)


def _request(
    plan: ExecutionPlan,
    snapshot: RepositorySnapshot,
    **overrides: object,
) -> LiveAuthorizationRequest:
    created_at = datetime(2026, 7, 21, 18, 0, tzinfo=UTC)
    payload: dict[str, object] = {
        "authorization_id": "live-auth-001",
        "actor": "gonzalo",
        "plan_hash": plan.plan_hash,
        "repository_snapshot_hash": snapshot.snapshot_hash,
        "scope": scope_for_live_execution(plan),
        "created_at": created_at,
        "expires_at": created_at + timedelta(minutes=10),
        "nonce": "live-nonce-1234567890",
        "reason": "Approve one bounded live test command.",
        "rollback_acknowledged": True,
    }
    payload.update(overrides)
    return LiveAuthorizationRequest.model_validate(payload)


def test_issue_live_authorization_for_non_denied_plan(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    plan = _plan(root)
    snapshot = RepositorySnapshot.capture(root)
    store = SQLiteLiveAuthorizationStore(tmp_path / "authority.db")

    receipt = issue_live_authorization(
        plan,
        snapshot,
        _request(plan, snapshot),
        _context(),
        store,
    )

    assert isinstance(receipt, LiveAuthorizationReceipt)
    assert receipt.plan_hash == plan.plan_hash
    assert receipt.repository_snapshot_hash == snapshot.snapshot_hash
    assert receipt.execution_reserved is False
    assert receipt.execution_performed is False
    assert store.get(receipt.receipt_id) == receipt


def test_denied_plan_cannot_receive_live_authority(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    plan = _plan(root, executable="rm")
    snapshot = RepositorySnapshot.capture(root)
    store = SQLiteLiveAuthorizationStore(tmp_path / "authority.db")

    with pytest.raises(PermissionError, match="denied"):
        issue_live_authorization(
            plan,
            snapshot,
            _request(plan, snapshot),
            _context(),
            store,
        )


def test_untrusted_actor_rejected(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    plan = _plan(root)
    snapshot = RepositorySnapshot.capture(root)
    store = SQLiteLiveAuthorizationStore(tmp_path / "authority.db")

    with pytest.raises(PermissionError, match="trusted"):
        issue_live_authorization(
            plan,
            snapshot,
            _request(plan, snapshot, actor="mallory"),
            _context(),
            store,
        )


def test_snapshot_mismatch_rejected(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    plan = _plan(root)
    snapshot = RepositorySnapshot.capture(root)
    store = SQLiteLiveAuthorizationStore(tmp_path / "authority.db")

    with pytest.raises(PermissionError, match="snapshot"):
        issue_live_authorization(
            plan,
            snapshot,
            _request(plan, snapshot, repository_snapshot_hash="0" * 64),
            _context(),
            store,
        )


def test_expired_request_rejected(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    plan = _plan(root)
    snapshot = RepositorySnapshot.capture(root)
    store = SQLiteLiveAuthorizationStore(tmp_path / "authority.db")

    with pytest.raises(PermissionError, match="expired"):
        issue_live_authorization(
            plan,
            snapshot,
            _request(plan, snapshot),
            _context(now=datetime(2026, 7, 21, 19, 0, tzinfo=UTC)),
            store,
        )


def test_nonce_replay_rejected(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    plan = _plan(root)
    snapshot = RepositorySnapshot.capture(root)
    store = SQLiteLiveAuthorizationStore(tmp_path / "authority.db")
    request = _request(plan, snapshot)

    issue_live_authorization(plan, snapshot, request, _context(), store)

    with pytest.raises(PermissionError, match="nonce"):
        issue_live_authorization(
            plan,
            snapshot,
            request.model_copy(update={"authorization_id": "live-auth-002"}),
            _context(),
            store,
        )


def test_receipt_survives_store_restart(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    plan = _plan(root)
    snapshot = RepositorySnapshot.capture(root)
    database = tmp_path / "authority.db"
    receipt = issue_live_authorization(
        plan,
        snapshot,
        _request(plan, snapshot),
        _context(),
        SQLiteLiveAuthorizationStore(database),
    )

    restarted = SQLiteLiveAuthorizationStore(database)

    assert restarted.get(receipt.receipt_id) == receipt


def test_database_tampering_is_detected(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    plan = _plan(root)
    snapshot = RepositorySnapshot.capture(root)
    database = tmp_path / "authority.db"
    store = SQLiteLiveAuthorizationStore(database)
    receipt = issue_live_authorization(
        plan,
        snapshot,
        _request(plan, snapshot),
        _context(),
        store,
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE live_authorization_receipts SET actor = ? WHERE receipt_id = ?",
            ("mallory", receipt.receipt_id),
        )
        connection.commit()

    with pytest.raises(PermissionError, match="integrity"):
        store.get(receipt.receipt_id)


def test_mark_executed_is_one_time_and_persistent(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    plan = _plan(root)
    snapshot = RepositorySnapshot.capture(root)
    database = tmp_path / "authority.db"
    store = SQLiteLiveAuthorizationStore(database)
    receipt = issue_live_authorization(
        plan,
        snapshot,
        _request(plan, snapshot),
        _context(),
        store,
    )

    reserved = store.reserve_execution(receipt.receipt_id)
    executed = store.mark_executed(receipt.receipt_id)

    assert reserved.execution_reserved is True
    assert executed.execution_reserved is True
    assert executed.execution_performed is True
    assert SQLiteLiveAuthorizationStore(database).get(receipt.receipt_id) == executed
    with pytest.raises(PermissionError, match="already"):
        store.mark_executed(receipt.receipt_id)
