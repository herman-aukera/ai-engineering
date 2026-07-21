"""Secure, bounded local-process adapter for authorized EACODE live plans.

The adapter accepts only a ``LiveExecutionPlan`` that passes the deterministic
pre-start guard. Process creation and cleanup are dependency-injected so CI can
verify lifecycle semantics without launching a real command.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from energy_core.controlled_execution import ExecutionPlan, _redact, _resolve_within, _truncate
from energy_core.execution_authorization import AuthorizationReceipt
from energy_core.live_execution_contract import LiveExecutionIntent, LiveExecutionPlan
from energy_core.live_execution_guard import (
    AuthorizationReceiptStore,
    LiveExecutionPolicy,
    verify_live_pre_start,
)
from energy_core.models import EnergyModel

FailureClass = Literal[
    "process_creation_failure",
    "timeout",
    "cancelled",
    "cleanup_failure",
    "stream_failure",
    "non_zero_exit",
    None,
]


class SecureProcessConfig(LiveExecutionPolicy):
    """Live execution policy plus bounded process-lifecycle controls."""

    poll_interval_seconds: float = Field(default=0.05, gt=0, le=1)
    cleanup_grace_seconds: float = Field(default=5.0, gt=0, le=30)


class SecureProcessResult(EnergyModel):
    """Sanitized result from one authorized process-start attempt."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    duration_ms: int = Field(default=0, ge=0)
    process_started: bool = False
    timed_out: bool = False
    cancelled: bool = False
    cleanup_verified: bool = False
    cleanup_error: str | None = None
    failure_class: FailureClass = None
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    redacted: bool = False


class _CancelEvent:
    def __init__(self) -> None:
        self._event = threading.Event()

    def set(self) -> None:
        self._event.set()

    def is_set(self) -> bool:
        return self._event.is_set()

    def clear(self) -> None:
        self._event.clear()


class _BoundedCollector:
    """Bound raw in-memory capture, then redact and truncate final output."""

    def __init__(self, output_limit: int) -> None:
        self._output_limit = output_limit
        self._capture_limit = output_limit + 4096
        self._parts: list[str] = []
        self._captured = 0
        self._truncated = False
        self._lock = threading.Lock()

    def add(self, value: str) -> None:
        with self._lock:
            remaining = self._capture_limit - self._captured
            if remaining <= 0:
                self._truncated = True
                return
            if len(value) > remaining:
                self._parts.append(value[:remaining])
                self._captured += remaining
                self._truncated = True
                return
            self._parts.append(value)
            self._captured += len(value)

    def finish(self) -> tuple[str, bool, bool]:
        raw = "".join(self._parts)
        redacted, changed = _redact(raw)
        bounded, final_truncated = _truncate(redacted, self._output_limit)
        return bounded, self._truncated or final_truncated, changed


class SecureProcessAdapter:
    """Execute one verified live plan and return normalized process evidence."""

    def __init__(
        self,
        config: SecureProcessConfig,
        *,
        receipt_store: AuthorizationReceiptStore,
        process_factory: Any | None = None,
        clock: Any | None = None,
        sleep: Any | None = None,
        cleanup: Any | None = None,
    ) -> None:
        self.config = config
        self._receipt_store = receipt_store
        self._process_factory = process_factory or subprocess.Popen
        self._clock = clock or time.monotonic
        self._sleep = sleep or time.sleep
        self._cleanup = cleanup or _terminate_process_tree
        self._cancel_event = _CancelEvent()

    def invoke(
        self,
        plan: ExecutionPlan,
        authorization_receipt: AuthorizationReceipt | None,
        live_intent: LiveExecutionIntent | None,
    ) -> SecureProcessResult:
        verify_live_pre_start(
            plan,
            self.config,
            authorization_receipt,
            live_intent=live_intent,
            receipt_store=self._receipt_store,
        )
        assert isinstance(plan, LiveExecutionPlan)
        assert authorization_receipt is not None
        assert live_intent is not None

        executable_path = _resolve_executable(plan.executable)
        root = Path(self.config.repository_root).resolve(strict=True)
        working_directory = _resolve_working_directory(plan, root)
        environment = _build_environment(plan, self.config)
        _verify_declared_paths(plan, root)

        # Recompute authority and repository state immediately before Popen.
        verify_live_pre_start(
            plan,
            self.config,
            authorization_receipt,
            live_intent=live_intent,
            receipt_store=self._receipt_store,
        )

        self._cancel_event.clear()
        started_at = self._clock()
        try:
            process = self._process_factory(
                args=[executable_path, *plan.arguments],
                cwd=str(working_directory),
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                shell=False,
                **_process_group_options(sys.platform),
            )
        except Exception as exc:
            return SecureProcessResult(
                duration_ms=_elapsed_ms(self._clock, started_at),
                process_started=False,
                cleanup_verified=False,
                cleanup_error=f"Process creation failed: {type(exc).__name__}",
                failure_class="process_creation_failure",
            )

        stdout_collector = _BoundedCollector(plan.max_output_chars)
        stderr_collector = _BoundedCollector(plan.max_output_chars)
        stream_errors: list[str] = []

        def read_stream(stream: Any, collector: _BoundedCollector, name: str) -> None:
            try:
                while True:
                    chunk = stream.read(4096)
                    if not chunk:
                        break
                    collector.add(chunk.decode("utf-8", errors="replace"))
            except Exception as exc:  # pragma: no cover - OS pipe edge
                stream_errors.append(f"{name}:{type(exc).__name__}")

        stdout_thread = threading.Thread(
            target=read_stream,
            args=(process.stdout, stdout_collector, "stdout"),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=read_stream,
            args=(process.stderr, stderr_collector, "stderr"),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()

        deadline = started_at + plan.timeout_seconds
        timed_out = False
        cancelled = False
        while process.poll() is None:
            if self._cancel_event.is_set():
                cancelled = True
                break
            if self._clock() >= deadline:
                timed_out = True
                break
            self._sleep(self.config.poll_interval_seconds)

        cleanup_verified = True
        cleanup_error: str | None = None
        if timed_out or cancelled:
            cleanup_verified, cleanup_error = self._cleanup(
                process,
                self.config.cleanup_grace_seconds,
            )
        else:
            try:
                process.wait(timeout=self.config.cleanup_grace_seconds)
                cleanup_verified = process.poll() is not None
                if not cleanup_verified:
                    cleanup_error = "Natural process completion could not be verified."
            except subprocess.TimeoutExpired:
                cleanup_verified, cleanup_error = self._cleanup(
                    process,
                    self.config.cleanup_grace_seconds,
                )

        stdout_thread.join(timeout=self.config.cleanup_grace_seconds)
        stderr_thread.join(timeout=self.config.cleanup_grace_seconds)
        stdout, stdout_truncated, stdout_redacted = stdout_collector.finish()
        stderr, stderr_truncated, stderr_redacted = stderr_collector.finish()

        if not cleanup_verified:
            failure_class: FailureClass = "cleanup_failure"
        elif stream_errors:
            failure_class = "stream_failure"
        elif timed_out:
            failure_class = "timeout"
        elif cancelled:
            failure_class = "cancelled"
        elif process.returncode not in (0, None):
            failure_class = "non_zero_exit"
        else:
            failure_class = None

        return SecureProcessResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=process.returncode,
            duration_ms=_elapsed_ms(self._clock, started_at),
            process_started=True,
            timed_out=timed_out,
            cancelled=cancelled,
            cleanup_verified=cleanup_verified,
            cleanup_error=cleanup_error or (";".join(stream_errors) or None),
            failure_class=failure_class,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            redacted=stdout_redacted or stderr_redacted,
        )

    def cancel(self) -> None:
        self._cancel_event.set()


def _process_group_options(platform: str) -> dict[str, object]:
    if platform == "win32":
        flag = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
        return {"creationflags": flag}
    return {"start_new_session": True}


def _resolve_executable(executable: str) -> str:
    resolved = shutil.which(executable)
    if resolved is None:
        raise PermissionError(f"Executable not found on PATH: {executable}")
    return resolved


def _resolve_working_directory(plan: ExecutionPlan, root: Path) -> Path:
    try:
        return _resolve_within(
            root,
            root,
            plan.working_directory,
            must_exist=True,
        )
    except ValueError as exc:
        raise PermissionError(str(exc)) from exc


def _verify_declared_paths(plan: ExecutionPlan, root: Path) -> None:
    for raw_path in plan.declared_paths:
        try:
            resolved = (root / raw_path).resolve(strict=False)
        except OSError as exc:
            raise PermissionError(f"Cannot resolve declared path: {raw_path}") from exc
        if not resolved.is_relative_to(root):
            raise PermissionError(f"Declared path escapes repository root: {raw_path}")


def _build_environment(
    plan: ExecutionPlan,
    policy: LiveExecutionPolicy,
) -> dict[str, str]:
    environment: dict[str, str] = {}
    for name in plan.environment_names:
        if name not in policy.environment_allowlist:
            raise PermissionError(f"Environment name not allowlisted: {name}")
        environment[name] = os.environ.get(name, "")
    environment["PATH"] = os.environ.get("PATH", "")
    if sys.platform == "win32":
        environment["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "C:\\Windows")
    return environment


def _terminate_process_tree(process: Any, grace_seconds: float) -> tuple[bool, str | None]:
    if process.poll() is not None:
        return True, None
    if sys.platform == "win32":
        return _terminate_windows_tree(process, grace_seconds)
    return _terminate_unix_group(process, grace_seconds)


def _terminate_windows_tree(process: Any, grace_seconds: float) -> tuple[bool, str | None]:
    completed = subprocess.run(
        ["taskkill", "/F", "/T", "/PID", str(process.pid)],
        capture_output=True,
        timeout=max(1.0, grace_seconds),
        shell=False,
        check=False,
    )
    try:
        process.wait(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        return False, "taskkill returned but the process remained alive."
    if process.poll() is None:
        return False, "Windows process-tree termination was not verified."
    if completed.returncode not in (0, 128):
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        return False, f"taskkill failed with {completed.returncode}: {detail}"
    return True, None


def _terminate_unix_group(process: Any, grace_seconds: float) -> tuple[bool, str | None]:
    try:
        group_id = os.getpgid(process.pid)
        if group_id != process.pid:
            return False, "Child process is not leader of its dedicated process group."
        os.killpg(group_id, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except OSError as exc:
        return False, f"killpg failed: {type(exc).__name__}"
    try:
        process.wait(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        return False, "Unix process group remained alive after SIGKILL."
    if process.poll() is None:
        return False, "Unix process-group cleanup was not verified."
    return True, None


def _elapsed_ms(clock: Any, started_at: float) -> int:
    return max(0, int((clock() - started_at) * 1000))
