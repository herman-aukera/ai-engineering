"""Atomic execution-reservation tests for one-time live authority."""

from __future__ import annotations  # noqa: I001

import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from energy_core.controlled_execution import CommandProposal, ExecutionPlan, build_execution_plan
from energy_core.live_authorization import (
    LiveAuthorizationContext,
    LiveAuthorizationRequest,
    SQLiteLiveAuthorizationStore,
    issue_live_authorization,
    scope_for_live_execution,
)
from energy_core.live_execution_contract import RepositorySnapshot, authorize_live_execution
from energy_core.live_execution_guard import LiveExecutionPolicy, verify_live_pre_start


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


def _plan(root: Path) -> ExecutionPlan:
    return build_execution_plan(
        CommandProposal(
            proposal_id="proposal-reservation",
            executable="pytest",
            arguments=["-q"],
            working_directory=".",
            requested_mode="fake",
            timeout_seconds=30,
            max_output_chars=1024,
            rollback_summary="Read-only test execution.",
        ),
        repository_root=root,
    )


def _issued(
    tmp_path: Path,
) -> tuple[
    Path,
    ExecutionPlan,
    RepositorySnapshot,
    SQLiteLiveAuthorizationStore,
    object,
]:
    root = _repository(tmp_path)
    plan = _plan(root)
    snapshot = RepositorySnapshot.capture(root)
    now = datetime.now(UTC)
    request = LiveAuthorizationRequest(
        authorization_id="live-auth-reservation",
        actor="gonzalo",
        plan_hash=plan.plan_hash,
        repository_snapshot_hash=snapshot.snapshot_hash,
        scope=scope_for_live_execution(plan),
        created_at=now - timedelta(seconds=1),
        expires_at=now + timedelta(minutes=5),
        nonce="reservation-nonce-123456",
        reason="Authorize one bounded process attempt.",
        rollback_acknowledged=True,
    )
    context = LiveAuthorizationContext(
        current_revision=1,
        trusted_actors=["gonzalo"],
        now=now,
    )
    store = SQLiteLiveAuthorizationStore(tmp_path / "authority.db")
    receipt = issue_live_authorization(plan, snapshot, request, context, store)
    return root, plan, snapshot, store, receipt


def test_receipt_is_not_reserved_when_issued(tmp_path: Path) -> None:
    _root, _plan_value, _snapshot, store, receipt = _issued(tmp_path)

    assert receipt.execution_reserved is False
    assert store.is_execution_reserved(receipt.receipt_id) is False


def test_reservation_is_atomic_and_one_time(tmp_path: Path) -> None:
    _root, _plan_value, _snapshot, store, receipt = _issued(tmp_path)

    reserved = store.reserve_execution(receipt.receipt_id)

    assert reserved.execution_reserved is True
    assert reserved.execution_performed is False
    with pytest.raises(PermissionError, match="reserved"):
        store.reserve_execution(receipt.receipt_id)


def test_reservation_survives_restart(tmp_path: Path) -> None:
    _root, _plan_value, _snapshot, store, receipt = _issued(tmp_path)
    reserved = store.reserve_execution(receipt.receipt_id)

    restarted = SQLiteLiveAuthorizationStore(store.database_path)

    assert restarted.get(receipt.receipt_id) == reserved
    assert restarted.is_execution_reserved(receipt.receipt_id) is True


def test_prestart_rejects_unreserved_receipt(tmp_path: Path) -> None:
    root, plan, snapshot, store, receipt = _issued(tmp_path)
    live_plan, intent = authorize_live_execution(plan, receipt, snapshot)
    policy = LiveExecutionPolicy(
        enabled=True,
        repository_root=str(root),
        current_revision=1,
        trusted_actors=["gonzalo"],
    )

    with pytest.raises(PermissionError, match="reserved"):
        verify_live_pre_start(
            live_plan,
            policy,
            receipt,
            live_intent=intent,
            receipt_store=store,
        )


def test_prestart_accepts_authoritatively_reserved_receipt(tmp_path: Path) -> None:
    root, plan, snapshot, store, receipt = _issued(tmp_path)
    live_plan, intent = authorize_live_execution(plan, receipt, snapshot)
    reserved = store.reserve_execution(receipt.receipt_id)
    policy = LiveExecutionPolicy(
        enabled=True,
        repository_root=str(root),
        current_revision=1,
        trusted_actors=["gonzalo"],
    )

    verify_live_pre_start(
        live_plan,
        policy,
        reserved,
        live_intent=intent,
        receipt_store=store,
    )
