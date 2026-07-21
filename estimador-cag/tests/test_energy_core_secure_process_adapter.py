"""Deterministic lifecycle tests for the secure Spec 0009 process adapter."""

from __future__ import annotations  # noqa: I001

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from energy_core.controlled_execution import CommandProposal, ExecutionPlan, build_execution_plan
from energy_core.execution_authorization import AuthorizationReceipt
from energy_core.live_execution_contract import (
    LiveExecutionIntent,
    LiveExecutionPlan,
    RepositorySnapshot,
    authorize_live_execution,
)
from energy_core.live_execution_guard import InMemoryAuthorizationReceiptStore
from energy_core.secure_process_adapter import (
    SecureProcessAdapter,
    SecureProcessConfig,
    _process_group_options,
)


class ChunkStream:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = list(chunks)

    def read(self, _size: int) -> bytes:
        return self._chunks.pop(0) if self._chunks else b""


class FakeProcess:
    def __init__(
        self,
        *,
        stdout_chunks: list[bytes] | None = None,
        stderr_chunks: list[bytes] | None = None,
        poll_values: list[int | None] | None = None,
        returncode: int = 0,
    ) -> None:
        self.stdout = ChunkStream(stdout_chunks or [b""])
        self.stderr = ChunkStream(stderr_chunks or [b""])
        self.pid = 4242
        self.returncode: int | None = None
        self._poll_values = list(poll_values or [returncode])
        self._final_returncode = returncode

    def poll(self) -> int | None:
        value = self._poll_values.pop(0) if self._poll_values else self._final_returncode
        if value is not None:
            self.returncode = value
        return value

    def wait(self, timeout: float | None = None) -> int:
        del timeout
        self.returncode = self._final_returncode
        return self._final_returncode


class StepClock:
    def __init__(self, values: list[float]) -> None:
        self._values = list(values)
        self._last = values[-1]

    def __call__(self) -> float:
        if self._values:
            self._last = self._values.pop(0)
        return self._last


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


def _base_plan(root: Path, *, timeout_seconds: int = 30) -> ExecutionPlan:
    return build_execution_plan(
        CommandProposal(
            proposal_id="proposal-secure-process",
            executable="pytest",
            arguments=["-q"],
            working_directory=".",
            requested_mode="fake",
            timeout_seconds=timeout_seconds,
            max_output_chars=128,
            rollback_summary="Read-only test execution.",
        ),
        repository_root=root,
    )


def _receipt(plan: ExecutionPlan) -> AuthorizationReceipt:
    return AuthorizationReceipt(
        receipt_id="receipt-secure-process",
        authorization_id="authorization-secure-process",
        actor="gonzalo",
        plan_hash=plan.plan_hash,
        accepted_revision=1,
        nonce_hash="d" * 64,
        consumed_at=datetime.now(UTC),
        execution_performed=False,
    )


def _live_contract(
    root: Path,
    *,
    timeout_seconds: int = 30,
) -> tuple[LiveExecutionPlan, LiveExecutionIntent, AuthorizationReceipt]:
    base_plan = _base_plan(root, timeout_seconds=timeout_seconds)
    receipt = _receipt(base_plan)
    snapshot = RepositorySnapshot.capture(root)
    live_plan, intent = authorize_live_execution(
        base_plan,
        receipt,
        snapshot,
        now=datetime.now(UTC),
    )
    return live_plan, intent, receipt


def _config(root: Path, **overrides: object) -> SecureProcessConfig:
    payload: dict[str, object] = {
        "enabled": True,
        "repository_root": str(root),
        "current_revision": 1,
        "trusted_actors": ["gonzalo"],
        "poll_interval_seconds": 0.01,
        "cleanup_grace_seconds": 0.1,
    }
    payload.update(overrides)
    return SecureProcessConfig.model_validate(payload)


def _adapter(
    root: Path,
    receipt: AuthorizationReceipt,
    process: FakeProcess,
    *,
    clock: Any | None = None,
    sleep: Any | None = None,
    cleanup: Any | None = None,
    calls: list[dict[str, Any]] | None = None,
) -> SecureProcessAdapter:
    records = calls if calls is not None else []

    def factory(**kwargs: Any) -> FakeProcess:
        records.append(kwargs)
        return process

    return SecureProcessAdapter(
        _config(root),
        receipt_store=InMemoryAuthorizationReceiptStore([receipt]),
        process_factory=factory,
        clock=clock,
        sleep=sleep,
        cleanup=cleanup,
    )


def test_adapter_uses_argument_list_shell_false_and_process_group(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    plan, intent, receipt = _live_contract(root)
    process = FakeProcess(stdout_chunks=[b"ok\n"])
    calls: list[dict[str, Any]] = []
    adapter = _adapter(root, receipt, process, calls=calls)

    result = adapter.invoke(plan, receipt, intent)

    assert result.process_started is True
    assert result.exit_code == 0
    assert result.cleanup_verified is True
    assert calls[0]["args"][-2:] == ["-q"] or calls[0]["args"][-1:] == ["-q"]
    assert isinstance(calls[0]["args"], list)
    assert calls[0]["shell"] is False
    assert calls[0].get("start_new_session") is True


def test_non_live_plan_rejected_before_process_factory(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    base_plan = _base_plan(root)
    receipt = _receipt(base_plan)
    calls: list[dict[str, Any]] = []
    adapter = _adapter(root, receipt, FakeProcess(), calls=calls)

    with pytest.raises(PermissionError, match="typed live"):
        adapter.invoke(base_plan, receipt, None)
    assert calls == []


def test_process_creation_failure_is_not_execution_performed(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    plan, intent, receipt = _live_contract(root)

    def failing_factory(**_kwargs: Any) -> FakeProcess:
        raise OSError("simulated creation failure")

    adapter = SecureProcessAdapter(
        _config(root),
        receipt_store=InMemoryAuthorizationReceiptStore([receipt]),
        process_factory=failing_factory,
    )
    result = adapter.invoke(plan, receipt, intent)

    assert result.process_started is False
    assert result.failure_class == "process_creation_failure"
    assert result.cleanup_verified is False


def test_timeout_uses_verified_cleanup(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    plan, intent, receipt = _live_contract(root, timeout_seconds=1)
    process = FakeProcess(poll_values=[None, None, None])
    cleanup_calls: list[int] = []

    def cleanup(candidate: FakeProcess, _grace: float) -> tuple[bool, str | None]:
        cleanup_calls.append(candidate.pid)
        candidate.wait()
        return True, None

    adapter = _adapter(
        root,
        receipt,
        process,
        clock=StepClock([0.0, 0.0, 2.0, 2.0]),
        sleep=lambda _seconds: None,
        cleanup=cleanup,
    )
    result = adapter.invoke(plan, receipt, intent)

    assert result.timed_out is True
    assert result.failure_class == "timeout"
    assert result.cleanup_verified is True
    assert cleanup_calls == [process.pid]


def test_cancellation_is_polled_before_normal_timeout(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    plan, intent, receipt = _live_contract(root)
    process = FakeProcess(poll_values=[None, None, None])
    cleanup_calls: list[int] = []
    holder: dict[str, SecureProcessAdapter] = {}

    def cleanup(candidate: FakeProcess, _grace: float) -> tuple[bool, str | None]:
        cleanup_calls.append(candidate.pid)
        candidate.wait()
        return True, None

    def cancel_on_first_sleep(_seconds: float) -> None:
        holder["adapter"].cancel()

    adapter = _adapter(
        root,
        receipt,
        process,
        clock=StepClock([0.0, 0.0, 0.1, 0.2]),
        sleep=cancel_on_first_sleep,
        cleanup=cleanup,
    )
    holder["adapter"] = adapter
    result = adapter.invoke(plan, receipt, intent)

    assert result.cancelled is True
    assert result.failure_class == "cancelled"
    assert result.duration_ms < plan.timeout_seconds * 1000
    assert cleanup_calls == [process.pid]


def test_cleanup_failure_fails_closed(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    plan, intent, receipt = _live_contract(root, timeout_seconds=1)
    process = FakeProcess(poll_values=[None, None, None])
    adapter = _adapter(
        root,
        receipt,
        process,
        clock=StepClock([0.0, 2.0, 2.0]),
        sleep=lambda _seconds: None,
        cleanup=lambda _process, _grace: (False, "cleanup unverified"),
    )

    result = adapter.invoke(plan, receipt, intent)

    assert result.failure_class == "cleanup_failure"
    assert result.cleanup_verified is False
    assert result.cleanup_error == "cleanup unverified"


def test_final_redaction_catches_secret_split_across_chunks(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    plan, intent, receipt = _live_contract(root)
    process = FakeProcess(
        stdout_chunks=[b"prefix sk-abcdefghij", b"klmnopqrstuvwxyz123456 suffix"]
    )
    adapter = _adapter(root, receipt, process)

    result = adapter.invoke(plan, receipt, intent)

    assert result.redacted is True
    assert "sk-" not in result.stdout
    assert "[REDACTED]" in result.stdout


def test_output_budget_sets_truncation_flag(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    plan, intent, receipt = _live_contract(root)
    process = FakeProcess(stdout_chunks=[b"X" * 512])
    adapter = _adapter(root, receipt, process)

    result = adapter.invoke(plan, receipt, intent)

    assert result.stdout_truncated is True
    assert len(result.stdout) <= plan.max_output_chars


def test_process_group_options_are_platform_specific() -> None:
    assert _process_group_options("linux") == {"start_new_session": True}
    windows = _process_group_options("win32")
    assert "creationflags" in windows
    assert windows["creationflags"] != 0
