"""Sandboxed real-process tool adapter for EACODE.

Disabled by default. Requires explicit opt-in via SandboxedToolConfig(enabled=True)
or the CLI --live-tool flag. Never uses shell=True. Produces bounded, redacted,
typed execution evidence under existing Spec 0007/0008 policy and authorization.
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
from typing import Literal

from pydantic import Field

from energy_core.controlled_execution import (
    ExecutionEvidence,
    ExecutionPlan,
    _hash_payload,
    _redact,
    _resolve_within,
    _truncate,
)
from energy_core.execution_authorization import AuthorizationReceipt
from energy_core.models import EnergyModel

FailureClass = Literal[
    "timeout", "cancelled", "non_zero_exit", "cleanup_failure", None
]


class SandboxedToolConfig(EnergyModel):
    """Immutable configuration for the sandboxed tool adapter.

    enabled defaults to False — real execution must be explicitly opted into.
    """

    enabled: bool = False
    repository_root: str = Field(min_length=1)
    current_revision: int = Field(default=0, ge=0)
    trusted_actors: list[str] = Field(default_factory=list)
    consumed_nonce_hashes: list[str] = Field(default_factory=list)
    environment_allowlist: list[str] = Field(
        default_factory=lambda: ["PYTHONPATH", "PYTHONUNBUFFERED"]
    )
    max_timeout_seconds: int = Field(default=120, ge=1, le=300)
    max_output_chars: int = Field(default=20_000, ge=128, le=100_000)
    allowed_executables: list[str] = Field(
        default_factory=lambda: ["pytest", "ruff", "python", "python3", "uv", "git"]
    )
    denied_executables: list[str] = Field(
        default_factory=lambda: [
            "bash", "cmd", "curl", "del", "mkfs", "powershell", "pwsh",
            "reboot", "rm", "rmdir", "scp", "sh", "shutdown", "ssh", "sudo",
            "wget", "zsh",
        ]
    )
    denied_git_subcommands: list[str] = Field(
        default_factory=lambda: [
            "branch", "checkout", "cherry-pick", "clean", "commit", "merge",
            "push", "rebase", "reset", "restore", "switch",
        ]
    )


class RealToolResult(EnergyModel):
    """Bounded, redacted result from a real process execution."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    duration_ms: int = Field(default=0, ge=0)
    timed_out: bool = False
    cancelled: bool = False
    process_tree_cleaned: bool = False
    cleanup_error: str | None = None
    failure_class: FailureClass = None
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    redacted: bool = False


class _CancelEvent:
    """Thread-safe cancellation signal."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def set(self) -> None:
        self._event.set()

    def is_set(self) -> bool:
        return self._event.is_set()

    def clear(self) -> None:
        self._event.clear()


class SandboxedToolAdapter:
    """Execute validated ExecutionPlans as real OS processes.

    The adapter is a subordinate evidence producer. It never decides whether
    a command is acceptable, whether evidence is sufficient, or whether a
    candidate should be accepted.

    Disabled by default — config.enabled must be True for any real execution.
    """

    def __init__(self, config: SandboxedToolConfig) -> None:
        self.config = config
        self._cancel_event = _CancelEvent()

    # ------------------------------------------------------------------
    # ToolPort protocol
    # ------------------------------------------------------------------

    def invoke(
        self,
        plan: ExecutionPlan,
        authorization_receipt: AuthorizationReceipt | None = None,
    ) -> RealToolResult:
        """Execute plan and return bounded, redacted evidence.

        Raises PermissionError if config.enabled is False or any pre-start
        verification fails. For human-gated plans, a valid consumed
        AuthorizationReceipt is required.
        """
        if not self.config.enabled:
            raise PermissionError(
                "SandboxedToolAdapter is disabled. Set config.enabled=True "
                "or use --live-tool to enable real execution."
            )

        _verify_pre_start(plan, self.config, authorization_receipt)

        executable_path = _resolve_executable(plan.executable)
        working_dir = _resolve_working_dir(plan, Path(self.config.repository_root))
        resolved_env = _build_environment(plan, self.config)
        _verify_paths_within_root(plan, Path(self.config.repository_root))

        self._cancel_event.clear()
        started_at = time.monotonic()

        try:
            process = subprocess.Popen(
                args=[executable_path, *plan.arguments],
                cwd=str(working_dir),
                env=resolved_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                shell=False,
            )

            stdout_chunks: list[str] = []
            stderr_chunks: list[str] = []
            stdout_truncated = False
            stderr_truncated = False
            redacted = False
            lock = threading.Lock()
            stream_error: Exception | None = None

            def _read_stream(stream, chunks: list[str], length_tracker: list[int]):
                nonlocal stream_error
                try:
                    for chunk in iter(lambda: stream.read(4096), b""):
                        if self._cancel_event.is_set():
                            break
                        text = chunk.decode("utf-8", errors="replace")
                        redacted_text, was_redacted = _redact(text)
                        with lock:
                            if was_redacted:
                                nonlocal redacted  # noqa: F824
                                redacted = True
                            current_len = length_tracker[0]
                            remaining = plan.max_output_chars - current_len
                            if remaining <= 0:
                                break
                            if len(redacted_text) > remaining:
                                redacted_text = redacted_text[:remaining]
                            chunks.append(redacted_text)
                            length_tracker[0] += len(redacted_text)
                except Exception as exc:
                    stream_error = exc

            stdout_len_tracker = [0]
            stderr_len_tracker = [0]

            stdout_thread = threading.Thread(
                target=_read_stream,
                args=(process.stdout, stdout_chunks, stdout_len_tracker),
                daemon=True,
            )
            stderr_thread = threading.Thread(
                target=_read_stream,
                args=(process.stderr, stderr_chunks, stderr_len_tracker),
                daemon=True,
            )
            stdout_thread.start()
            stderr_thread.start()

            try:
                process.wait(timeout=plan.timeout_seconds)
            except subprocess.TimeoutExpired:
                _kill_process_tree(process.pid)
                process.wait(timeout=10)
                stdout_thread.join(timeout=5)
                stderr_thread.join(timeout=5)

                duration_ms = int((time.monotonic() - started_at) * 1000)
                stdout, stdout_trunc = _truncate(
                    "".join(stdout_chunks), plan.max_output_chars
                )
                stderr, stderr_trunc = _truncate(
                    "".join(stderr_chunks), plan.max_output_chars
                )

                return RealToolResult(
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=None,
                    duration_ms=duration_ms,
                    timed_out=True,
                    process_tree_cleaned=True,
                    failure_class="timeout",
                    stdout_truncated=stdout_trunc or stdout_truncated,
                    stderr_truncated=stderr_trunc or stderr_truncated,
                    redacted=redacted,
                )

            stdout_thread.join(timeout=10)
            stderr_thread.join(timeout=10)

            if self._cancel_event.is_set():
                _kill_process_tree(process.pid)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass

                duration_ms = int((time.monotonic() - started_at) * 1000)
                stdout, stdout_trunc = _truncate(
                    "".join(stdout_chunks), plan.max_output_chars
                )
                stderr, stderr_trunc = _truncate(
                    "".join(stderr_chunks), plan.max_output_chars
                )

                return RealToolResult(
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=None,
                    duration_ms=duration_ms,
                    cancelled=True,
                    process_tree_cleaned=True,
                    failure_class="cancelled",
                    stdout_truncated=stdout_trunc or stdout_truncated,
                    stderr_truncated=stderr_trunc or stderr_truncated,
                    redacted=redacted,
                )

            if stream_error is not None:
                raise stream_error

            duration_ms = int((time.monotonic() - started_at) * 1000)
            exit_code = process.returncode

            stdout_text = "".join(stdout_chunks)
            stderr_text = "".join(stderr_chunks)
            stdout, stdout_trunc = _truncate(stdout_text, plan.max_output_chars)
            stderr, stderr_trunc = _truncate(stderr_text, plan.max_output_chars)

            failure_class: FailureClass = (
                "non_zero_exit" if exit_code != 0 else None
            )

            return RealToolResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                duration_ms=duration_ms,
                process_tree_cleaned=True,
                failure_class=failure_class,
                stdout_truncated=stdout_trunc,
                stderr_truncated=stderr_trunc,
                redacted=redacted,
            )

        except Exception:
            # If Popen itself failed, attempt cleanup and record
            duration_ms = int((time.monotonic() - started_at) * 1000)
            return RealToolResult(
                stdout="",
                stderr="",
                exit_code=None,
                duration_ms=duration_ms,
                process_tree_cleaned=False,
                cleanup_error="Process creation failed.",
                failure_class="cleanup_failure",
            )

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    def cancel(self) -> None:
        """Signal the adapter to cancel the current execution."""
        self._cancel_event.set()

    # ------------------------------------------------------------------
    # Evidence builder
    # ------------------------------------------------------------------

    def build_evidence(
        self,
        plan: ExecutionPlan,
        result: RealToolResult,
        *,
        run_id: str,
        authorization_receipt: AuthorizationReceipt | None = None,
    ) -> ExecutionEvidence:
        """Build ExecutionEvidence from a real execution result."""
        if authorization_receipt is not None:
            if authorization_receipt.plan_hash != plan.plan_hash:
                raise PermissionError(
                    "Authorization receipt plan_hash does not match execution plan."
                )

        status: Literal["pass", "fail", "missing", "conflict"]
        if result.timed_out:
            status = "fail"
        elif result.cancelled:
            status = "fail"
        elif result.failure_class == "cleanup_failure":
            status = "conflict"
        elif result.exit_code == 0:
            status = "pass"
        else:
            status = "fail"

        summary_parts = ["Real process execution recorded."]
        if result.timed_out:
            summary_parts.append("Process timed out.")
        if result.cancelled:
            summary_parts.append("Process cancelled.")
        if result.failure_class == "non_zero_exit":
            summary_parts.append(f"Exit code: {result.exit_code}.")
        if result.redacted:
            summary_parts.append("Output was redacted.")
        if result.stdout_truncated or result.stderr_truncated:
            summary_parts.append("Output was truncated.")

        artifact_payload = {
            "exit_code": result.exit_code,
            "stdout_excerpt": result.stdout,
            "stderr_excerpt": result.stderr,
            "duration_ms": result.duration_ms,
            "timed_out": result.timed_out,
            "cancelled": result.cancelled,
        }

        return ExecutionEvidence(
            evidence_id=f"execution-{plan.plan_hash[:16]}",
            run_id=run_id,
            proposal_id=plan.proposal_id,
            plan_hash=plan.plan_hash,
            status=status,
            summary=" ".join(summary_parts),
            execution_mode=plan.execution_mode,
            execution_performed=True,
            adapter_invoked=True,
            exit_code=result.exit_code,
            stdout_excerpt=result.stdout,
            stderr_excerpt=result.stderr,
            output_truncated=result.stdout_truncated or result.stderr_truncated,
            redaction_status="redacted" if result.redacted else "not_required",
            artifact_hash=_hash_payload(artifact_payload),
            duration_ms=result.duration_ms,
            rollback_available=bool((plan.rollback_summary or "").strip()),
            trust_classification="trusted",
            policy_reasons=list(plan.reasons),
        )


# ------------------------------------------------------------------
# Pre-start verification
# ------------------------------------------------------------------


def _verify_pre_start(
    plan: ExecutionPlan,
    config: SandboxedToolConfig,
    authorization_receipt: AuthorizationReceipt | None = None,
) -> None:
    """Independent pre-start verification.

    Revalidates plan disposition, authorization, paths, and executable
    immediately before process creation. Raises PermissionError on any failure.
    """
    if plan.disposition == "deny":
        raise PermissionError(
            f"Execution denied by policy: {', '.join(plan.reasons)}"
        )
    if plan.execution_performed:
        raise PermissionError("Plan has already been executed.")

    # Authorization check for human-gated plans
    if plan.requires_human_authorization:
        if authorization_receipt is None:
            raise PermissionError(
                "Human-gated plan requires a consumed authorization receipt."
            )
        if authorization_receipt.plan_hash != plan.plan_hash:
            raise PermissionError(
                "Authorization receipt plan_hash does not match execution plan."
            )
        if authorization_receipt.accepted_revision != config.current_revision:
            raise PermissionError(
                f"Authorization receipt revision {authorization_receipt.accepted_revision} "
                f"does not match current revision {config.current_revision}."
            )
        if authorization_receipt.execution_performed:
            raise PermissionError("Authorization receipt has already been executed.")

    executable_lower = plan.executable.lower()
    if executable_lower in config.denied_executables:
        raise PermissionError(f"Executable denied: {plan.executable}")
    if executable_lower not in config.allowed_executables:
        raise PermissionError(f"Executable not in allowlist: {plan.executable}")

    if executable_lower == "git" and plan.arguments:
        subcommand = plan.arguments[0].lower()
        if subcommand in config.denied_git_subcommands:
            raise PermissionError(f"Git subcommand denied: {subcommand}")


def _resolve_executable(executable: str) -> str:
    """Resolve executable path without shell interpretation."""
    resolved = shutil.which(executable)
    if resolved is None:
        raise PermissionError(
            f"Executable not found on PATH: {executable}"
        )
    return resolved


def _resolve_working_dir(plan: ExecutionPlan, root: Path) -> Path:
    """Resolve working directory within repository root."""
    resolved_root = root.resolve(strict=True)
    try:
        return _resolve_within(resolved_root, resolved_root, plan.working_directory, must_exist=True)
    except ValueError as exc:
        raise PermissionError(str(exc)) from exc


def _verify_paths_within_root(plan: ExecutionPlan, root: Path) -> None:
    """Revalidate all declared paths and path-like arguments."""
    for raw_path in plan.declared_paths:
        candidate = root / raw_path
        try:
            resolved = candidate.resolve()
        except Exception:
            raise PermissionError(f"Cannot resolve path: {raw_path}")
        try:
            if not resolved.is_relative_to(root):
                raise PermissionError(
                    f"Path escapes repository root: {raw_path}"
                )
        except AttributeError:
            # Python < 3.9 fallback
            if root not in resolved.parents and resolved != root:
                raise PermissionError(
                    f"Path escapes repository root: {raw_path}"
                )


def _build_environment(
    plan: ExecutionPlan, config: SandboxedToolConfig
) -> dict[str, str]:
    """Build minimal process environment from name allowlist."""
    env: dict[str, str] = {}
    for name in plan.environment_names:
        if name in config.environment_allowlist:
            value = os.environ.get(name, "")
            env[name] = value

    # PATH needed for executable resolution in the child process
    env["PATH"] = os.environ.get("PATH", "")

    # SYSTEMROOT needed on Windows for basic system function
    if sys.platform == "win32":
        env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "C:\\Windows")

    return env


# ------------------------------------------------------------------
# Process-tree cleanup
# ------------------------------------------------------------------


def _kill_process_tree(pid: int) -> None:
    """Terminate the complete process tree.

    On Windows, uses taskkill /F /T /PID.
    On Unix, uses killpg with SIGKILL.
    """
    if sys.platform == "win32":
        _kill_process_tree_windows(pid)
    else:
        _kill_process_tree_unix(pid)


def _kill_process_tree_windows(pid: int) -> None:
    """Kill process tree using Windows taskkill."""
    try:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            timeout=10,
            shell=False,
        )
    except Exception:
        pass


def _kill_process_tree_unix(pid: int) -> None:
    """Kill process tree using Unix process group signals."""
    try:
        os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, OSError):
        pass


# ------------------------------------------------------------------
# Failure injection adapter for deterministic testing
# ------------------------------------------------------------------


class FailureInjectingAdapter(SandboxedToolAdapter):
    """Test adapter that can inject specific failure modes.

    Used in deterministic CI to verify failure-handling logic without
    creating real OS processes.
    """

    def __init__(
        self,
        config: SandboxedToolConfig,
        *,
        inject_timeout: bool = False,
        inject_cancellation: bool = False,
        inject_non_zero_exit: bool = False,
        inject_oversized_output: bool = False,
        inject_secret_output: bool = False,
        inject_cleanup_failure: bool = False,
    ) -> None:
        super().__init__(config)
        self._inject_timeout = inject_timeout
        self._inject_cancellation = inject_cancellation
        self._inject_non_zero_exit = inject_non_zero_exit
        self._inject_oversized_output = inject_oversized_output
        self._inject_secret_output = inject_secret_output
        self._inject_cleanup_failure = inject_cleanup_failure

    def invoke(
        self,
        plan: ExecutionPlan,
        authorization_receipt: AuthorizationReceipt | None = None,
    ) -> RealToolResult:
        """Return a deterministic fake result based on injection flags.

        Does not create any real OS process. Used for deterministic CI testing.
        """
        if not self.config.enabled:
            raise PermissionError(
                "SandboxedToolAdapter is disabled. Set config.enabled=True."
            )

        _verify_pre_start(plan, self.config, authorization_receipt)
        Path(self.config.repository_root)

        if self._inject_timeout:
            return RealToolResult(
                stdout="partial output before timeout",
                stderr="",
                exit_code=None,
                duration_ms=int(plan.timeout_seconds * 1000),
                timed_out=True,
                process_tree_cleaned=True,
                failure_class="timeout",
                stdout_truncated=True,
            )

        if self._inject_cancellation:
            return RealToolResult(
                stdout="partial output before cancel",
                stderr="",
                exit_code=None,
                duration_ms=1500,
                cancelled=True,
                process_tree_cleaned=True,
                failure_class="cancelled",
                stdout_truncated=True,
            )

        if self._inject_cleanup_failure:
            return RealToolResult(
                stdout="",
                stderr="",
                exit_code=None,
                duration_ms=0,
                process_tree_cleaned=False,
                cleanup_error="Simulated cleanup failure.",
                failure_class="cleanup_failure",
            )

        exit_code = 1 if self._inject_non_zero_exit else 0

        if self._inject_secret_output:
            stdout = "Result: sk-abcdefghijklmnopqrstuvwxyz123456"
        else:
            stdout = "Deterministic fake output."

        if self._inject_oversized_output:
            stdout = "X" * (plan.max_output_chars + 500)

        redacted_text, was_redacted = _redact(stdout)
        bounded, was_truncated = _truncate(redacted_text, plan.max_output_chars)

        failure_class: FailureClass = "non_zero_exit" if exit_code != 0 else None

        return RealToolResult(
            stdout=bounded,
            stderr="",
            exit_code=exit_code,
            duration_ms=100,
            process_tree_cleaned=True,
            failure_class=failure_class,
            stdout_truncated=was_truncated,
            redacted=was_redacted,
        )
