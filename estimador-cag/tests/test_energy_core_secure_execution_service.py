"""Evidence and one-time authority tests for secure live execution."""

from __future__ import annotations  # noqa: I001

import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

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
from energy_core.secure_execution_service import (
    LiveExecutionEvidence,
    SecureExecutionService,
)
from energy_core.secure_process_adapter import SecureProcessResult


class StubAdapter:
    def __init__(self, result: SecureProcessResult) -> None:
        self.result = result
        self.calls: list[tuple[object, object, object]] = []

    def invoke(self, plan: object, receipt: object, intent: object) -> SecureProcessResult:
        assert getattr(receipt, "execution_reserved") is True
        self.calls.append((plan, receipt, intent))
        return self.result


class FailingCompletionStore:
    def __init__(self, delegate: SQLiteLiveAuthorizationStore) -> None:
        self.delegate = delegate

    def get(self, receipt_id: str) -> object:
        return self.delegate.get(receipt_id)

    def is_execution_reserved(self, receipt_id: str) -> bool:
        return self.delegate.is_execution_reserved(receipt_id)

    def reserve_execution(self, receipt_id: str) -> object:
        return self.delegate.reserve_execution(receipt_id)

    def mark_executed(self, receipt_id: str) -> object:
        del receipt_id
        raise PermissionError("simulated completion persistence failure")


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
            proposal_id="proposal-secure-service",
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


def _authority(
    tmp_path: Path,
) -> tuple[object, object, object, SQLiteLiveAuthorizationStore]:
    root = _repository(tmp_path)
    plan = _plan(root)
    snapshot = RepositorySnapshot.capture(root)
    now = datetime.now(UTC)
    store = SQLiteLiveAuthorizationStore(tmp_path / "authority.db")
    receipt = issue_live_authorization(
        plan,
        snapshot,
        LiveAuthorizationRequest(
            authorization_id="live-auth-service",
            actor="gonzalo",
            plan_hash=plan.plan_hash,
            repository_snapshot_hash=snapshot.snapshot_hash,
            scope=scope_for_live_execution(plan),
            created_at=now - timedelta(seconds=1),
            expires_at=now + timedelta(minutes=5),
            nonce="secure-service-nonce-123456",
            reason="Authorize one bounded process attempt.",
            rollback_acknowledged=True,
        ),
        LiveAuthorizationContext(
            current_revision=1,
            trusted_actors=["gonzalo"],
            now=now,
        ),
        store,
    )
    live_plan, intent = authorize_live_execution(plan, receipt, snapshot, now=now)
    return live_plan, intent, receipt, store


def _result(**overrides: Any) -> SecureProcessResult:
    payload: dict[str, Any] = {
        "stdout": "ok\n",
        "stderr": "",
        "exit_code": 0,
        "duration_ms": 25,
        "process_started": True,
        "cleanup_verified": True,
    }
    payload.update(overrides)
    return SecureProcessResult.model_validate(payload)


def test_success_marks_receipt_executed_and_builds_pass_evidence(tmp_path: Path) -> None:
    plan, intent, receipt, store = _authority(tmp_path)
    adapter = StubAdapter(_result())
    service = SecureExecutionService(adapter=adapter, receipt_store=store)

    outcome = service.execute(plan, intent, receipt, run_id="run-pass")

    assert outcome.evidence.status == "pass"
    assert outcome.evidence.execution_performed is True
    assert outcome.evidence.authority_reserved is True
    assert outcome.evidence.authority_completion_verified is True
    assert outcome.final_receipt is not None
    assert outcome.final_receipt.execution_performed is True
    assert store.get(receipt.receipt_id) == outcome.final_receipt
    assert len(adapter.calls) == 1


def test_process_creation_failure_stays_reserved_and_not_executed(tmp_path: Path) -> None:
    plan, intent, receipt, store = _authority(tmp_path)
    adapter = StubAdapter(
        _result(
            stdout="",
            exit_code=None,
            process_started=False,
            cleanup_verified=False,
            failure_class="process_creation_failure",
        )
    )
    service = SecureExecutionService(adapter=adapter, receipt_store=store)

    outcome = service.execute(plan, intent, receipt, run_id="run-no-start")

    persisted = store.get(receipt.receipt_id)
    assert outcome.evidence.status == "missing"
    assert outcome.evidence.execution_performed is False
    assert persisted is not None
    assert persisted.execution_reserved is True
    assert persisted.execution_performed is False
    with pytest.raises(PermissionError, match="reserved"):
        service.execute(plan, intent, receipt, run_id="run-replay")


def test_timeout_is_fail_but_execution_completion_is_recorded(tmp_path: Path) -> None:
    plan, intent, receipt, store = _authority(tmp_path)
    service = SecureExecutionService(
        adapter=StubAdapter(
            _result(
                exit_code=None,
                timed_out=True,
                failure_class="timeout",
            )
        ),
        receipt_store=store,
    )

    outcome = service.execute(plan, intent, receipt, run_id="run-timeout")

    assert outcome.evidence.status == "fail"
    assert outcome.evidence.execution_performed is True
    assert outcome.evidence.authority_completion_verified is True


def test_cleanup_failure_is_conflict_and_untrusted(tmp_path: Path) -> None:
    plan, intent, receipt, store = _authority(tmp_path)
    service = SecureExecutionService(
        adapter=StubAdapter(
            _result(
                exit_code=None,
                cleanup_verified=False,
                cleanup_error="cleanup unverified",
                failure_class="cleanup_failure",
            )
        ),
        receipt_store=store,
    )

    outcome = service.execute(plan, intent, receipt, run_id="run-cleanup")

    assert outcome.evidence.status == "conflict"
    assert outcome.evidence.trust_classification == "unknown"
    assert outcome.evidence.cleanup_verified is False


def test_completion_store_failure_is_conflict_and_fail_closed(tmp_path: Path) -> None:
    plan, intent, receipt, store = _authority(tmp_path)
    service = SecureExecutionService(
        adapter=StubAdapter(_result()),
        receipt_store=FailingCompletionStore(store),
    )

    outcome = service.execute(plan, intent, receipt, run_id="run-store-failure")

    assert outcome.evidence.status == "conflict"
    assert outcome.evidence.authority_completion_verified is False
    assert outcome.evidence.trust_classification == "unknown"
    assert "completion" in outcome.evidence.summary.lower()


def test_live_evidence_converts_to_standard_evidence_record(tmp_path: Path) -> None:
    plan, intent, receipt, store = _authority(tmp_path)
    service = SecureExecutionService(adapter=StubAdapter(_result()), receipt_store=store)

    evidence = service.execute(
        plan,
        intent,
        receipt,
        run_id="run-record",
    ).evidence
    record = evidence.to_evidence_record()

    assert record.type == "controlled_live_execution"
    assert record.command_hash == evidence.live_plan_hash
    assert record.provenance["base_plan_hash"] == evidence.base_plan_hash
    assert record.provenance["authorization_receipt_id"] == receipt.receipt_id
    assert record.provenance["repository_snapshot_hash"] == plan.repository_snapshot_hash


def test_live_evidence_round_trip_and_no_self_approval(tmp_path: Path) -> None:
    plan, intent, receipt, store = _authority(tmp_path)
    evidence = SecureExecutionService(
        adapter=StubAdapter(_result()),
        receipt_store=store,
    ).execute(plan, intent, receipt, run_id="run-roundtrip").evidence

    reloaded = LiveExecutionEvidence.model_validate(evidence.model_dump(mode="json"))

    assert reloaded == evidence
    assert not hasattr(evidence, "decision")
    assert not hasattr(evidence, "accepted")
