"""Typed authority transition from non-executing plans to live execution.

Planning remains dry-run or fake by default. A live plan exists only after a
consumed authorization receipt is bound to an immutable repository snapshot.
The process adapter remains a subordinate evidence producer and never grants
its own authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from energy_core.controlled_execution import ExecutionPlan
from energy_core.execution_authorization import AuthorizationReceipt
from energy_core.models import EnergyModel


class RepositorySnapshot(EnergyModel):
    """Immutable digest of the complete Git working state used for authority."""

    repository_root: str = Field(min_length=1)
    head_sha: str = Field(pattern=r"^[a-f0-9]{40,64}$")
    tree_sha: str = Field(pattern=r"^[a-f0-9]{40,64}$")
    staged_diff_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    unstaged_diff_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    untracked_state_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    snapshot_hash: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_snapshot_hash(self) -> RepositorySnapshot:
        if self.snapshot_hash != self.calculate_snapshot_hash():
            raise ValueError("snapshot_hash does not match repository snapshot")
        return self

    @classmethod
    def capture(cls, repository_root: str | Path) -> RepositorySnapshot:
        root = Path(repository_root).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("repository_root must be a directory")

        payload = {
            "repository_root": str(root),
            "head_sha": _git_text(root, "rev-parse", "HEAD"),
            "tree_sha": _git_text(root, "rev-parse", "HEAD^{tree}"),
            "staged_diff_digest": _sha256_bytes(
                _git_bytes(
                    root,
                    "diff",
                    "--cached",
                    "--binary",
                    "--no-ext-diff",
                    "--no-textconv",
                )
            ),
            "unstaged_diff_digest": _sha256_bytes(
                _git_bytes(
                    root,
                    "diff",
                    "--binary",
                    "--no-ext-diff",
                    "--no-textconv",
                )
            ),
            "untracked_state_digest": _untracked_state_digest(root),
        }
        return cls(snapshot_hash=_sha256_json(payload), **payload)

    def calculate_snapshot_hash(self) -> str:
        return _sha256_json(
            self.model_dump(mode="json", exclude={"snapshot_hash"})
        )

    def verify_current(self) -> None:
        current = type(self).capture(self.repository_root)
        fields = (
            "repository_root",
            "head_sha",
            "tree_sha",
            "staged_diff_digest",
            "unstaged_diff_digest",
            "untracked_state_digest",
            "snapshot_hash",
        )
        changed = [
            field for field in fields if getattr(current, field) != getattr(self, field)
        ]
        if changed:
            raise PermissionError(
                "Repository snapshot mismatch: " + ", ".join(changed)
            )


class LiveExecutionPlan(ExecutionPlan):
    """Explicit live variant derived from one validated non-executing plan."""

    execution_mode: Literal["live"] = "live"
    base_plan_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    live_intent_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    repository_snapshot_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    authorization_receipt_id: str = Field(min_length=1, max_length=240)

    @model_validator(mode="after")
    def validate_live_plan_hash(self) -> LiveExecutionPlan:
        if self.plan_hash != self.calculate_live_plan_hash():
            raise ValueError("plan_hash does not match live execution plan")
        return self

    def calculate_live_plan_hash(self) -> str:
        payload = self.model_dump(
            mode="json",
            exclude={"plan_hash", "plan_id"},
        )
        return _sha256_json(payload)


class LiveExecutionIntent(EnergyModel):
    """Exact, expiring authority for one live execution transition."""

    schema_version: str = "1.0.0"
    intent_id: str = Field(min_length=1, max_length=200)
    base_plan_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    authorization_id: str = Field(min_length=1, max_length=200)
    authorization_receipt_id: str = Field(min_length=1, max_length=240)
    actor: str = Field(min_length=1, max_length=240)
    repository_snapshot: RepositorySnapshot
    executable: str = Field(min_length=1, max_length=80)
    arguments: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    working_directory: str = Field(min_length=1, max_length=500)
    environment_names: tuple[str, ...] = Field(default_factory=tuple, max_length=32)
    timeout_seconds: int = Field(ge=1, le=300)
    max_output_chars: int = Field(ge=128, le=100_000)
    created_at: datetime
    expires_at: datetime
    intent_hash: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_contract(self) -> LiveExecutionIntent:
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise ValueError("expires_at must be timezone-aware")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be later than created_at")
        if self.intent_hash != self.calculate_intent_hash():
            raise ValueError("intent_hash does not match live execution intent")
        return self

    def calculate_intent_hash(self) -> str:
        return _sha256_json(
            self.model_dump(mode="json", exclude={"intent_hash"})
        )

    def verify_for(
        self,
        plan: LiveExecutionPlan,
        receipt: AuthorizationReceipt,
        *,
        now: datetime | None = None,
    ) -> None:
        current_time = now or datetime.now(UTC)
        reasons: list[str] = []
        if current_time.tzinfo is None or current_time.utcoffset() is None:
            reasons.append("verification_time_not_timezone_aware")
        elif current_time < self.created_at:
            reasons.append("live_intent_not_yet_valid")
        elif current_time >= self.expires_at:
            reasons.append("live_intent_expired")
        if plan.plan_hash != plan.calculate_live_plan_hash():
            reasons.append("live_plan_hash_mismatch")
        if self.base_plan_hash != plan.base_plan_hash:
            reasons.append("base_plan_hash_mismatch")
        if receipt.plan_hash != plan.base_plan_hash:
            reasons.append("authorization_plan_hash_mismatch")
        if self.authorization_id != receipt.authorization_id:
            reasons.append("authorization_id_mismatch")
        if self.authorization_receipt_id != receipt.receipt_id:
            reasons.append("authorization_receipt_id_mismatch")
        if self.actor != receipt.actor:
            reasons.append("authorization_actor_mismatch")
        if receipt.execution_performed:
            reasons.append("authorization_already_executed")
        if plan.live_intent_hash != self.intent_hash:
            reasons.append("live_intent_hash_mismatch")
        if plan.repository_snapshot_hash != self.repository_snapshot.snapshot_hash:
            reasons.append("repository_snapshot_hash_mismatch")
        if plan.authorization_receipt_id != receipt.receipt_id:
            reasons.append("live_plan_receipt_id_mismatch")
        if self.executable != plan.executable:
            reasons.append("executable_mismatch")
        if self.arguments != tuple(plan.arguments):
            reasons.append("arguments_mismatch")
        if self.working_directory != plan.working_directory:
            reasons.append("working_directory_mismatch")
        if self.environment_names != tuple(plan.environment_names):
            reasons.append("environment_names_mismatch")
        if self.timeout_seconds != plan.timeout_seconds:
            reasons.append("timeout_mismatch")
        if self.max_output_chars != plan.max_output_chars:
            reasons.append("output_budget_mismatch")
        if reasons:
            raise PermissionError("Live execution intent denied: " + ", ".join(reasons))
        self.repository_snapshot.verify_current()


def authorize_live_execution(
    plan: ExecutionPlan,
    receipt: AuthorizationReceipt,
    snapshot: RepositorySnapshot,
    *,
    now: datetime | None = None,
    ttl_seconds: int = 300,
) -> tuple[LiveExecutionPlan, LiveExecutionIntent]:
    """Promote one validated non-executing plan through explicit authority."""

    created_at = now or datetime.now(UTC)
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    if not 1 <= ttl_seconds <= 900:
        raise ValueError("ttl_seconds must be between 1 and 900")
    if plan.disposition == "deny":
        raise PermissionError("Denied plans cannot be promoted to live execution")
    if plan.execution_performed:
        raise PermissionError("Plan has already been executed")
    if receipt.plan_hash != plan.plan_hash:
        raise PermissionError("Authorization receipt plan_hash mismatch")
    if receipt.execution_performed:
        raise PermissionError("Authorization receipt has already been executed")

    plan_root = Path(plan.repository_root).resolve(strict=True)
    snapshot_root = Path(snapshot.repository_root).resolve(strict=True)
    if plan_root != snapshot_root:
        raise PermissionError("Repository snapshot root does not match execution plan")
    snapshot.verify_current()

    intent_payload = {
        "schema_version": "1.0.0",
        "intent_id": f"live-intent-{plan.plan_hash[:16]}",
        "base_plan_hash": plan.plan_hash,
        "authorization_id": receipt.authorization_id,
        "authorization_receipt_id": receipt.receipt_id,
        "actor": receipt.actor,
        "repository_snapshot": snapshot,
        "executable": plan.executable,
        "arguments": tuple(plan.arguments),
        "working_directory": plan.working_directory,
        "environment_names": tuple(plan.environment_names),
        "timeout_seconds": plan.timeout_seconds,
        "max_output_chars": plan.max_output_chars,
        "created_at": created_at,
        "expires_at": created_at + timedelta(seconds=ttl_seconds),
    }
    intent_draft = LiveExecutionIntent.model_construct(
        intent_hash="0" * 64,
        **intent_payload,
    )
    intent = LiveExecutionIntent(
        intent_hash=intent_draft.calculate_intent_hash(),
        **intent_payload,
    )

    live_payload = plan.model_dump(mode="python")
    live_payload.update(
        {
            "plan_id": "pending",
            "plan_hash": "0" * 64,
            "execution_mode": "live",
            "base_plan_hash": plan.plan_hash,
            "live_intent_hash": intent.intent_hash,
            "repository_snapshot_hash": snapshot.snapshot_hash,
            "authorization_receipt_id": receipt.receipt_id,
            "execution_performed": False,
        }
    )
    live_draft = LiveExecutionPlan.model_construct(**live_payload)
    live_hash = live_draft.calculate_live_plan_hash()
    live_payload["plan_id"] = f"live-plan-{live_hash[:16]}"
    live_payload["plan_hash"] = live_hash
    live_plan = LiveExecutionPlan.model_validate(live_payload)
    return live_plan, intent


def _git_text(root: Path, *args: str) -> str:
    value = _git_bytes(root, *args).decode("utf-8", errors="strict").strip()
    if not value:
        raise PermissionError(f"Git command returned empty output: {' '.join(args)}")
    return value


def _git_bytes(root: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(root),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        shell=False,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0:
        error = completed.stderr.decode("utf-8", errors="replace").strip()
        raise PermissionError(
            f"Cannot capture repository snapshot for {' '.join(args)}: {error}"
        )
    return completed.stdout


def _untracked_state_digest(root: Path) -> str:
    raw_paths = _git_bytes(
        root,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
    ).split(b"\0")
    entries: list[dict[str, object]] = []
    for raw_path in sorted(path for path in raw_paths if path):
        relative = os.fsdecode(raw_path)
        candidate = root / relative
        try:
            metadata = candidate.lstat()
        except FileNotFoundError as exc:
            raise PermissionError(
                f"Untracked path disappeared during snapshot: {relative}"
            ) from exc

        if stat.S_ISLNK(metadata.st_mode):
            kind = "symlink"
            content = os.fsencode(os.readlink(candidate))
        elif stat.S_ISREG(metadata.st_mode):
            kind = "file"
            content = candidate.read_bytes()
        else:
            kind = "other"
            content = str(metadata.st_mode).encode("ascii")
        entries.append(
            {
                "path": Path(relative).as_posix(),
                "kind": kind,
                "size": metadata.st_size,
                "content_digest": _sha256_bytes(content),
            }
        )
    return _sha256_json(entries)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=_json_default,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _json_default(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, EnergyModel):
        return value.model_dump(mode="json")
    raise TypeError(f"Object is not JSON serializable: {type(value).__name__}")
