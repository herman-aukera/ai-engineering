from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from energy_core.controlled_execution import (
    CommandProposal,
    ExecutionPlan,
    build_execution_plan,
)
from energy_core.execution_authorization import AuthorizationReceipt
from energy_core.live_execution_contract import (
    LiveExecutionPlan,
    RepositorySnapshot,
    authorize_live_execution,
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


def _base_plan(root: Path, *, requested_mode: str = "fake") -> ExecutionPlan:
    return build_execution_plan(
        CommandProposal(
            proposal_id="proposal-live-contract",
            executable="pytest",
            arguments=["-q"],
            working_directory=".",
            requested_mode=requested_mode,
            timeout_seconds=30,
            max_output_chars=1024,
            rollback_summary="Read-only test execution.",
        ),
        repository_root=root,
    )


def _receipt(plan: ExecutionPlan, **overrides: object) -> AuthorizationReceipt:
    payload: dict[str, object] = {
        "receipt_id": "receipt-live-contract",
        "authorization_id": "authorization-live-contract",
        "actor": "gonzalo",
        "plan_hash": plan.plan_hash,
        "accepted_revision": 1,
        "nonce_hash": "a" * 64,
        "consumed_at": datetime(2026, 7, 21, 18, 0, tzinfo=UTC),
        "execution_performed": False,
    }
    payload.update(overrides)
    return AuthorizationReceipt.model_validate(payload)


def test_command_proposal_still_rejects_direct_live_mode(tmp_path: Path) -> None:
    _repository(tmp_path)
    with pytest.raises(ValidationError):
        _base_plan(tmp_path, requested_mode="live")


def test_authority_transition_creates_distinct_live_plan(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    base_plan = _base_plan(root)
    receipt = _receipt(base_plan)
    snapshot = RepositorySnapshot.capture(root)

    live_plan, intent = authorize_live_execution(
        base_plan,
        receipt,
        snapshot,
        now=datetime(2026, 7, 21, 18, 1, tzinfo=UTC),
    )

    assert isinstance(live_plan, LiveExecutionPlan)
    assert live_plan.execution_mode == "live"
    assert live_plan.base_plan_hash == base_plan.plan_hash
    assert live_plan.plan_hash != base_plan.plan_hash
    assert live_plan.live_intent_hash == intent.intent_hash
    assert live_plan.repository_snapshot_hash == snapshot.snapshot_hash
    assert live_plan.authorization_receipt_id == receipt.receipt_id


def test_transition_rejects_receipt_for_another_plan(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    base_plan = _base_plan(root)
    receipt = _receipt(base_plan, plan_hash="0" * 64)
    snapshot = RepositorySnapshot.capture(root)

    with pytest.raises(PermissionError, match="plan_hash"):
        authorize_live_execution(base_plan, receipt, snapshot)


def test_snapshot_detects_untracked_content_change_without_head_change(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    scratch = root / "scratch.txt"
    scratch.write_text("before\n", encoding="utf-8")
    snapshot = RepositorySnapshot.capture(root)
    original_head = snapshot.head_sha

    scratch.write_text("after\n", encoding="utf-8")

    with pytest.raises(PermissionError, match="untracked_state_digest"):
        snapshot.verify_current()
    assert RepositorySnapshot.capture(root).head_sha == original_head


def test_snapshot_detects_staged_and_unstaged_changes(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    snapshot = RepositorySnapshot.capture(root)

    (root / "tracked.txt").write_text("changed\n", encoding="utf-8")
    with pytest.raises(PermissionError, match="unstaged_diff_digest"):
        snapshot.verify_current()

    _git(root, "add", "tracked.txt")
    with pytest.raises(PermissionError, match="staged_diff_digest"):
        snapshot.verify_current()


def test_live_intent_expires_fail_closed(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    base_plan = _base_plan(root)
    receipt = _receipt(base_plan)
    snapshot = RepositorySnapshot.capture(root)
    created_at = datetime(2026, 7, 21, 18, 1, tzinfo=UTC)
    live_plan, intent = authorize_live_execution(
        base_plan,
        receipt,
        snapshot,
        now=created_at,
        ttl_seconds=30,
    )

    with pytest.raises(PermissionError, match="expired"):
        intent.verify_for(
            live_plan,
            receipt,
            now=datetime(2026, 7, 21, 18, 2, tzinfo=UTC),
        )


def test_live_plan_round_trip_preserves_authority_hashes(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    base_plan = _base_plan(root)
    receipt = _receipt(base_plan)
    snapshot = RepositorySnapshot.capture(root)
    live_plan, _ = authorize_live_execution(base_plan, receipt, snapshot)

    reloaded = LiveExecutionPlan.model_validate(live_plan.model_dump(mode="json"))

    assert reloaded == live_plan
    assert reloaded.calculate_live_plan_hash() == live_plan.plan_hash
