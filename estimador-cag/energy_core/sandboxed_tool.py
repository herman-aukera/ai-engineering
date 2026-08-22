"""Legacy Spec 0009 compatibility surface.

The historical real-process adapter is permanently disabled. Deterministic
failure injection remains available for regression tests and evidence fixtures.
All authorized OS execution must use ``SecureProcessAdapter`` through
``SecureExecutionService``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import Field

from energy_core.controlled_execution import (
    ExecutionEvidence,
    ExecutionPlan,
    _hash_payload,
    _redact,
    _truncate,
)
from energy_core.execution_authorization import AuthorizationReceipt
from energy_core.models import EnergyModel

FailureClass = Literal[
    "timeout",
    "cancelled",
    "non_zero_exit",
    "cleanup_failure",
    None,
]


class SandboxedToolConfig(EnergyModel):
    """Legacy configuration retained for fixture and API compatibility."""

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
            "bash",
            "cmd",
            "curl",
            "del",
            "mkfs",
            "powershell",
            "pwsh",
            "reboot",
            "rm",
            "rmdir",
            "scp",
            "sh",
            "shutdown",
            "ssh",
            "sudo",
            "wget",
            "zsh",
        ]
    )
    denied_git_subcommands: list[str] = Field(
        default_factory=lambda: [
            "branch",
            "checkout",
            "cherry-pick",
            "clean",
            "commit",
            "merge",
            "push",
            "rebase",
            "reset",
            "restore",
            "switch",
        ]
    )
    repository_snapshot: dict[str, str] | None = Field(default=None)


class RealToolResult(EnergyModel):
    """Legacy deterministic result contract retained for compatibility."""

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


class SandboxedToolAdapter:
    """Permanently disabled historical real-process adapter."""

    def __init__(self, config: SandboxedToolConfig) -> None:
        self.config = config

    def invoke(
        self,
        plan: ExecutionPlan,
        authorization_receipt: AuthorizationReceipt | None = None,
    ) -> RealToolResult:
        del authorization_receipt
        if not self.config.enabled:
            raise PermissionError("SandboxedToolAdapter is disabled.")
        if plan.execution_mode in {"dry_run", "fake"}:
            raise PermissionError(
                f"{plan.execution_mode} plans cannot reach the legacy real-process adapter."
            )
        raise PermissionError(
            "legacy real-process adapter is disabled; use SecureProcessAdapter "
            "through SecureExecutionService."
        )

    def cancel(self) -> None:
        """Compatibility no-op: this adapter never creates a process."""

    def build_evidence(
        self,
        plan: ExecutionPlan,
        result: RealToolResult,
        *,
        run_id: str,
        authorization_receipt: AuthorizationReceipt | None = None,
    ) -> ExecutionEvidence:
        if (
            authorization_receipt is not None
            and authorization_receipt.plan_hash != plan.plan_hash
        ):
            raise PermissionError("Receipt plan_hash mismatch.")
        if (
            authorization_receipt is not None
            and authorization_receipt.execution_performed
        ):
            raise PermissionError(
                "Authorization receipt execution_performed=True is not reusable."
            )
        return _build_legacy_evidence(plan, result, run_id=run_id)


class FailureInjectingAdapter(SandboxedToolAdapter):
    """Deterministic CI adapter that never creates an OS process."""

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
        _verify_failure_fixture_preconditions(
            plan,
            self.config,
            authorization_receipt,
        )

        if self._inject_timeout:
            return RealToolResult(
                stdout="partial output before timeout",
                exit_code=None,
                duration_ms=plan.timeout_seconds * 1000,
                timed_out=True,
                process_tree_cleaned=True,
                failure_class="timeout",
                stdout_truncated=True,
            )
        if self._inject_cancellation:
            return RealToolResult(
                stdout="partial output before cancel",
                exit_code=None,
                duration_ms=1500,
                cancelled=True,
                process_tree_cleaned=True,
                failure_class="cancelled",
                stdout_truncated=True,
            )
        if self._inject_cleanup_failure:
            return RealToolResult(
                exit_code=None,
                process_tree_cleaned=False,
                cleanup_error="Simulated cleanup failure.",
                failure_class="cleanup_failure",
            )

        exit_code = 1 if self._inject_non_zero_exit else 0
        stdout = (
            "Result: sk-abcdefghijklmnopqrstuvwxyz123456"  # test-secret-fixture
            if self._inject_secret_output
            else "Deterministic fake output."
        )
        if self._inject_oversized_output:
            stdout = "X" * (plan.max_output_chars + 500)

        redacted, was_redacted = _redact(stdout)
        bounded, was_truncated = _truncate(redacted, plan.max_output_chars)
        return RealToolResult(
            stdout=bounded,
            exit_code=exit_code,
            duration_ms=100,
            process_tree_cleaned=True,
            failure_class="non_zero_exit" if exit_code else None,
            stdout_truncated=was_truncated,
            redacted=was_redacted,
        )


def _verify_failure_fixture_preconditions(
    plan: ExecutionPlan,
    config: SandboxedToolConfig,
    authorization_receipt: AuthorizationReceipt | None,
) -> None:
    if not config.enabled:
        raise PermissionError("SandboxedToolAdapter is disabled.")
    if plan.disposition == "deny":
        raise PermissionError(
            f"Execution denied by policy: {', '.join(plan.reasons)}"
        )
    if plan.execution_performed:
        raise PermissionError("Plan has already been executed.")
    if plan.requires_human_authorization:
        if authorization_receipt is None:
            raise PermissionError(
                "Human-gated plan requires a consumed authorization receipt."
            )
        if authorization_receipt.plan_hash != plan.plan_hash:
            raise PermissionError("Receipt plan_hash mismatch.")
        if authorization_receipt.execution_performed:
            raise PermissionError(
                "Authorization receipt execution_performed=True is not reusable."
            )
        if authorization_receipt.accepted_revision != config.current_revision:
            raise PermissionError(
                "Authorization receipt revision does not match current revision."
            )

    executable = plan.executable.lower()
    if executable in config.denied_executables:
        raise PermissionError(f"Executable denied: {plan.executable}")
    if executable not in config.allowed_executables:
        raise PermissionError(f"Executable not in allowlist: {plan.executable}")
    if executable == "git" and plan.arguments:
        subcommand = plan.arguments[0].lower()
        if subcommand in config.denied_git_subcommands:
            raise PermissionError(f"Git subcommand denied: {subcommand}")

    if config.repository_snapshot:
        expected_head = config.repository_snapshot.get("head_sha", "")
        if expected_head:
            completed = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=config.repository_root,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            actual_head = completed.stdout.strip() if completed.returncode == 0 else ""
            if actual_head != expected_head:
                raise PermissionError(
                    "Repository snapshot mismatch for deterministic fixture."
                )


def _build_legacy_evidence(
    plan: ExecutionPlan,
    result: RealToolResult,
    *,
    run_id: str,
) -> ExecutionEvidence:
    if result.failure_class == "cleanup_failure":
        status: Literal["pass", "fail", "missing", "conflict"] = "conflict"
    elif result.failure_class is not None or result.exit_code not in (0, None):
        status = "fail"
    else:
        status = "pass"

    artifact_payload = {
        "exit_code": result.exit_code,
        "stdout_excerpt": result.stdout,
        "stderr_excerpt": result.stderr,
        "duration_ms": result.duration_ms,
        "timed_out": result.timed_out,
        "cancelled": result.cancelled,
        "process_tree_cleaned": result.process_tree_cleaned,
        "failure_class": result.failure_class,
    }
    return ExecutionEvidence(
        evidence_id=f"execution-{plan.plan_hash[:16]}",
        run_id=run_id,
        proposal_id=plan.proposal_id,
        plan_hash=plan.plan_hash,
        status=status,
        summary="Deterministic failure-injection evidence recorded.",
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
        trust_classification=(
            "unknown" if result.failure_class == "cleanup_failure" else "trusted"
        ),
        policy_reasons=list(plan.reasons),
    )


def _build_environment(
    plan: ExecutionPlan,
    config: SandboxedToolConfig,
) -> dict[str, str]:
    """Compatibility helper used by deterministic leakage tests."""

    environment: dict[str, str] = {}
    for name in plan.environment_names:
        if name in config.environment_allowlist:
            environment[name] = os.environ.get(name, "")
    environment["PATH"] = os.environ.get("PATH", "")
    if sys.platform == "win32":
        environment["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "C:\\Windows")
    return environment


def _kill_process_tree(pid: int) -> tuple[bool, str]:
    """Legacy kill helper is disabled because no process handle can be verified."""

    del pid
    return False, "Legacy cleanup is disabled and cannot be verified."


def _resolve_repository_root(config: SandboxedToolConfig) -> Path:
    """Return the validated root for compatibility callers."""

    return Path(config.repository_root).resolve(strict=True)
