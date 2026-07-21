"""Pre-start security tests for the Spec 0009 real-process boundary."""

from __future__ import annotations  # noqa: I001

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from energy_core.controlled_execution import CommandProposal, ExecutionPlan, build_execution_plan
from energy_core.execution_authorization import AuthorizationReceipt
from energy_core.live_execution_contract import (
    LiveExecutionIntent,
    LiveExecutionPlan,
    RepositorySnapshot,
    authorize_live_execution,
)
from energy_core.live_execution_guard import (
    InMemoryAuthorizationReceiptStore,
    LiveExecutionPolicy,
    verify_live_pre_start,
)


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )


def _repository(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "tests@example.invalid")
    _git(tmp_path, "config", "user.name", "EACODE Tests")
    (tmp_path / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(tmp_path, "add", "tracked.txt")
    _git(tmp_path, "commit", "-m", "initial")
    return tmp_path


def _base_plan(root: Path) -> ExecutionPlan:
    return build_execution_plan(
        CommandProposal(
            proposal_id="proposal-live-prestart",
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


def _receipt(plan: ExecutionPlan, **overrides: object) -> AuthorizationReceipt:
    payload: dict[str, object] = {
        "receipt_id": "receipt-live-prestart",
        "authorization_id": "authorization-live-prestart",
        "actor": "gonzalo",
        "plan_hash": plan.plan_hash,
        "accepted_revision": 1,
        "nonce_hash": "b" * 64,
        "consumed_at": datetime.now(UTC),
        "execution_performed": False,
    }
    payload.update(overrides)
    return AuthorizationReceipt.model_validate(payload)


def _live_contract(
    root: Path,
) -> tuple[LiveExecutionPlan, LiveExecutionIntent, AuthorizationReceipt]:
    base_plan = _base_plan(root)
    receipt = _receipt(base_plan)
    snapshot = RepositorySnapshot.capture(root)
    live_plan, intent = authorize_live_execution(
        base_plan,
        receipt,
        snapshot,
        now=datetime.now(UTC),
    )
    return live_plan, intent, receipt


def _policy(root: Path, **overrides: object) -> LiveExecutionPolicy:
    payload: dict[str, object] = {
        "enabled": True,
        "repository_root": str(root),
        "current_revision": 1,
        "trusted_actors": ["gonzalo"],
    }
    payload.update(overrides)
    return LiveExecutionPolicy.model_validate(payload)


def test_prestart_accepts_exact_live_contract(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    live_plan, intent, receipt = _live_contract(root)
    store = InMemoryAuthorizationReceiptStore([receipt])

    verify_live_pre_start(
        live_plan,
        _policy(root),
        receipt,
        live_intent=intent,
        receipt_store=store,
    )


def test_prestart_rejects_non_live_plan(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    base_plan = _base_plan(root)
    receipt = _receipt(base_plan)
    store = InMemoryAuthorizationReceiptStore([receipt])

    with pytest.raises(PermissionError, match="typed live"):
        verify_live_pre_start(
            base_plan,
            _policy(root),
            receipt,
            live_intent=None,
            receipt_store=store,
        )


def test_prestart_requires_authoritative_receipt_store(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    live_plan, intent, receipt = _live_contract(root)

    with pytest.raises(PermissionError, match="store"):
        verify_live_pre_start(
            live_plan,
            _policy(root),
            receipt,
            live_intent=intent,
            receipt_store=None,
        )


def test_prestart_rejects_fabricated_receipt_object(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    live_plan, intent, receipt = _live_contract(root)
    authoritative = receipt.model_copy(update={"nonce_hash": "c" * 64})
    store = InMemoryAuthorizationReceiptStore([authoritative])

    with pytest.raises(PermissionError, match="provenance"):
        verify_live_pre_start(
            live_plan,
            _policy(root),
            receipt,
            live_intent=intent,
            receipt_store=store,
        )


def test_prestart_rejects_repository_change_after_authorization(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    live_plan, intent, receipt = _live_contract(root)
    store = InMemoryAuthorizationReceiptStore([receipt])
    (root / "later.txt").write_text("changed after authority\n", encoding="utf-8")

    with pytest.raises(PermissionError, match="snapshot"):
        verify_live_pre_start(
            live_plan,
            _policy(root),
            receipt,
            live_intent=intent,
            receipt_store=store,
        )


def test_prestart_rejects_untrusted_actor(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    live_plan, intent, receipt = _live_contract(root)
    store = InMemoryAuthorizationReceiptStore([receipt])

    with pytest.raises(PermissionError, match="trusted"):
        verify_live_pre_start(
            live_plan,
            _policy(root, trusted_actors=["another-reviewer"]),
            receipt,
            live_intent=intent,
            receipt_store=store,
        )


def test_prestart_rejects_tampered_live_plan(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    live_plan, intent, receipt = _live_contract(root)
    store = InMemoryAuthorizationReceiptStore([receipt])
    tampered = live_plan.model_copy(update={"arguments": ["--version"]})

    with pytest.raises(PermissionError, match="hash"):
        verify_live_pre_start(
            tampered,
            _policy(root),
            receipt,
            live_intent=intent,
            receipt_store=store,
        )
