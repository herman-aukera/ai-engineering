"""Deterministic pre-start guard for authorized EACODE live execution."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import Field

from energy_core.controlled_execution import ExecutionPlan
from energy_core.execution_authorization import AuthorizationReceipt
from energy_core.live_execution_contract import LiveExecutionIntent, LiveExecutionPlan
from energy_core.models import EnergyModel


class AuthorizationReceiptStore(Protocol):
    """Authoritative source used to reject fabricated or replayed receipts."""

    def get(self, receipt_id: str) -> AuthorizationReceipt | None:
        """Return the authoritative receipt or ``None``."""

    def is_execution_reserved(self, receipt_id: str) -> bool:
        """Return whether the single process attempt was atomically reserved."""


class InMemoryAuthorizationReceiptStore:
    """Explicit test store; production execution uses persistent authority."""

    def __init__(
        self,
        receipts: list[AuthorizationReceipt] | None = None,
        *,
        reserved_receipt_ids: list[str] | None = None,
    ) -> None:
        self._receipts = {receipt.receipt_id: receipt for receipt in receipts or []}
        self._reserved = (
            set(self._receipts)
            if reserved_receipt_ids is None
            else set(reserved_receipt_ids)
        )

    def get(self, receipt_id: str) -> AuthorizationReceipt | None:
        return self._receipts.get(receipt_id)

    def is_execution_reserved(self, receipt_id: str) -> bool:
        return receipt_id in self._reserved

    def put(self, receipt: AuthorizationReceipt, *, reserved: bool = False) -> None:
        self._receipts[receipt.receipt_id] = receipt
        if reserved:
            self._reserved.add(receipt.receipt_id)

    def reserve_execution(self, receipt_id: str) -> AuthorizationReceipt:
        receipt = self.get(receipt_id)
        if receipt is None:
            raise PermissionError("Authorization receipt does not exist.")
        if receipt_id in self._reserved:
            raise PermissionError("Authorization receipt already reserved.")
        self._reserved.add(receipt_id)
        return receipt


class LiveExecutionPolicy(EnergyModel):
    """Fail-closed policy evaluated immediately before process creation."""

    enabled: bool = False
    repository_root: str = Field(min_length=1)
    current_revision: int = Field(default=0, ge=0)
    trusted_actors: list[str] = Field(default_factory=list)
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
    environment_allowlist: list[str] = Field(
        default_factory=lambda: ["PYTHONPATH", "PYTHONUNBUFFERED"]
    )
    max_timeout_seconds: int = Field(default=120, ge=1, le=300)
    max_output_chars: int = Field(default=20_000, ge=128, le=100_000)


def verify_live_pre_start(
    plan: ExecutionPlan,
    policy: LiveExecutionPolicy,
    authorization_receipt: AuthorizationReceipt | None,
    *,
    live_intent: LiveExecutionIntent | None,
    receipt_store: AuthorizationReceiptStore | None,
) -> None:
    """Verify exact authority, repository state, and process policy fail closed."""

    if not policy.enabled:
        raise PermissionError("Live execution policy is disabled.")
    if plan.disposition == "deny":
        raise PermissionError(
            f"Execution denied by policy: {', '.join(plan.reasons)}"
        )
    if plan.execution_performed:
        raise PermissionError("Plan has already been executed.")
    if not isinstance(plan, LiveExecutionPlan) or plan.execution_mode != "live":
        raise PermissionError(
            "Real execution requires an explicit typed live execution plan."
        )
    if live_intent is None:
        raise PermissionError("Live execution intent is required.")
    if authorization_receipt is None:
        raise PermissionError("Consumed authorization receipt is required.")
    if receipt_store is None:
        raise PermissionError("Authoritative authorization receipt store is required.")

    authoritative = receipt_store.get(authorization_receipt.receipt_id)
    if authoritative is None or authoritative != authorization_receipt:
        raise PermissionError("Authorization receipt provenance verification failed.")
    if not receipt_store.is_execution_reserved(authorization_receipt.receipt_id):
        raise PermissionError(
            "Authorization receipt execution attempt is not atomically reserved."
        )
    if authorization_receipt.plan_hash != plan.base_plan_hash:
        raise PermissionError("Authorization receipt plan_hash mismatch.")
    if authorization_receipt.accepted_revision != policy.current_revision:
        raise PermissionError(
            "Authorization receipt revision does not match current revision."
        )
    if authorization_receipt.execution_performed:
        raise PermissionError("Authorization receipt has already been executed.")
    if policy.trusted_actors and authorization_receipt.actor not in policy.trusted_actors:
        raise PermissionError("Authorization actor is not trusted.")

    policy_root = Path(policy.repository_root).resolve(strict=True)
    plan_root = Path(plan.repository_root).resolve(strict=True)
    snapshot_root = Path(
        live_intent.repository_snapshot.repository_root
    ).resolve(strict=True)
    if policy_root != plan_root or policy_root != snapshot_root:
        raise PermissionError("Repository root mismatch across live authority records.")

    executable = plan.executable.lower()
    if executable in policy.denied_executables:
        raise PermissionError(f"Executable denied: {plan.executable}")
    if executable not in policy.allowed_executables:
        raise PermissionError(f"Executable not in allowlist: {plan.executable}")
    if executable == "git" and plan.arguments:
        subcommand = plan.arguments[0].lower()
        if subcommand in policy.denied_git_subcommands:
            raise PermissionError(f"Git subcommand denied: {subcommand}")
    unknown_environment = sorted(
        set(plan.environment_names) - set(policy.environment_allowlist)
    )
    if unknown_environment:
        raise PermissionError(
            "Environment names not allowlisted: " + ", ".join(unknown_environment)
        )
    if plan.timeout_seconds > policy.max_timeout_seconds:
        raise PermissionError("Plan timeout exceeds live execution policy.")
    if plan.max_output_chars > policy.max_output_chars:
        raise PermissionError("Plan output budget exceeds live execution policy.")

    if plan.live_intent_hash != live_intent.intent_hash:
        raise PermissionError("Live intent hash mismatch.")
    if plan.repository_snapshot_hash != live_intent.repository_snapshot.snapshot_hash:
        raise PermissionError("Repository snapshot hash mismatch.")
    if plan.authorization_receipt_id != authorization_receipt.receipt_id:
        raise PermissionError("Authorization receipt identity mismatch.")

    live_intent.verify_for(plan, authorization_receipt)
