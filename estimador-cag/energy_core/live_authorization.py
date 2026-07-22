"""Persistent one-time authorization for EACODE live execution.

This module is distinct from the legacy human-gate authorization contract.
It authorizes one bounded live transition for any non-denied execution plan,
binds authority to an exact repository snapshot, persists the receipt in
SQLite, detects record tampering, rejects nonce replay, atomically reserves
one process attempt, and records execution completion exactly once.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import Field, ValidationError, model_validator

from energy_core.controlled_execution import ExecutionPlan
from energy_core.execution_authorization import AuthorizationReceipt
from energy_core.live_execution_contract import RepositorySnapshot
from energy_core.models import EnergyModel


class LiveExecutionScope(EnergyModel):
    """Exact process scope covered by one live authorization request."""

    executable: str = Field(min_length=1, max_length=80)
    arguments: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    working_directory: str = Field(min_length=1, max_length=500)
    environment_names: tuple[str, ...] = Field(default_factory=tuple, max_length=32)
    timeout_seconds: int = Field(ge=1, le=300)
    max_output_chars: int = Field(ge=128, le=100_000)


class LiveAuthorizationRequest(EnergyModel):
    """Human-issued request to authorize one exact live transition."""

    schema_version: str = "1.0.0"
    authorization_id: str = Field(min_length=1, max_length=160)
    actor: str = Field(min_length=1, max_length=240)
    plan_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    repository_snapshot_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    scope: LiveExecutionScope
    created_at: datetime
    expires_at: datetime
    nonce: str = Field(min_length=12, max_length=240)
    reason: str = Field(min_length=1, max_length=2_000)
    rollback_acknowledged: bool

    @model_validator(mode="after")
    def validate_temporal_contract(self) -> LiveAuthorizationRequest:
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise ValueError("expires_at must be timezone-aware")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be later than created_at")
        return self


class LiveAuthorizationContext(EnergyModel):
    """Trusted runtime context used to evaluate a live authorization request."""

    current_revision: int = Field(ge=0)
    trusted_actors: list[str] = Field(default_factory=list)
    now: datetime

    @model_validator(mode="after")
    def validate_context(self) -> LiveAuthorizationContext:
        if self.now.tzinfo is None or self.now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        if len(set(self.trusted_actors)) != len(self.trusted_actors):
            raise ValueError("trusted_actors must be unique")
        return self


class LiveAuthorizationReceipt(AuthorizationReceipt):
    """Integrity-protected receipt persisted by the authoritative store."""

    schema_version: str = "2.1.0"
    repository_snapshot_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    execution_reserved: bool = False
    record_hash: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_record_hash(self) -> LiveAuthorizationReceipt:
        if self.record_hash != self.calculate_record_hash():
            raise ValueError("record_hash does not match live authorization receipt")
        return self

    def calculate_record_hash(self) -> str:
        return _sha256_json(
            self.model_dump(mode="json", exclude={"record_hash"})
        )


class SQLiteLiveAuthorizationStore:
    """Trusted SQLite authority store with replay and reservation guards."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path).resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._setup()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def _setup(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS live_authorization_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    authorization_id TEXT NOT NULL UNIQUE,
                    actor TEXT NOT NULL,
                    plan_hash TEXT NOT NULL,
                    accepted_revision INTEGER NOT NULL,
                    nonce_hash TEXT NOT NULL UNIQUE,
                    consumed_at TEXT NOT NULL,
                    execution_reserved INTEGER NOT NULL DEFAULT 0,
                    execution_performed INTEGER NOT NULL CHECK (execution_performed IN (0, 1)),
                    repository_snapshot_hash TEXT NOT NULL,
                    record_hash TEXT NOT NULL
                )
                """
            )
            columns = {
                str(row["name"])
                for row in connection.execute(
                    "PRAGMA table_info(live_authorization_receipts)"
                ).fetchall()
            }
            if "execution_reserved" not in columns:
                connection.execute(
                    """
                    ALTER TABLE live_authorization_receipts
                    ADD COLUMN execution_reserved INTEGER NOT NULL DEFAULT 0
                    """
                )
            connection.commit()

    def issue(self, receipt: LiveAuthorizationReceipt) -> LiveAuthorizationReceipt:
        """Persist one receipt atomically; duplicate nonce or ID fails closed."""

        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    INSERT INTO live_authorization_receipts (
                        receipt_id,
                        authorization_id,
                        actor,
                        plan_hash,
                        accepted_revision,
                        nonce_hash,
                        consumed_at,
                        execution_reserved,
                        execution_performed,
                        repository_snapshot_hash,
                        record_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        receipt.receipt_id,
                        receipt.authorization_id,
                        receipt.actor,
                        receipt.plan_hash,
                        receipt.accepted_revision,
                        receipt.nonce_hash,
                        receipt.consumed_at.isoformat(),
                        int(receipt.execution_reserved),
                        int(receipt.execution_performed),
                        receipt.repository_snapshot_hash,
                        receipt.record_hash,
                    ),
                )
                connection.commit()
        except sqlite3.IntegrityError as exc:
            detail = str(exc).lower()
            if "nonce_hash" in detail:
                raise PermissionError("Live authorization nonce already consumed.") from exc
            raise PermissionError(
                "Live authorization ID or receipt already exists."
            ) from exc
        return receipt

    def get(self, receipt_id: str) -> LiveAuthorizationReceipt | None:
        with self._connect() as connection:
            row = _select_receipt(connection, receipt_id)
        if row is None:
            return None
        return _validated_receipt_from_row(row)

    def nonce_consumed(self, nonce_hash: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM live_authorization_receipts
                WHERE nonce_hash = ?
                """,
                (nonce_hash,),
            ).fetchone()
        return row is not None

    def is_execution_reserved(self, receipt_id: str) -> bool:
        receipt = self.get(receipt_id)
        return bool(receipt and receipt.execution_reserved)

    def reserve_execution(self, receipt_id: str) -> LiveAuthorizationReceipt:
        """Atomically claim the single process attempt before process creation."""

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = _select_receipt(connection, receipt_id)
            if row is None:
                raise PermissionError("Live authorization receipt does not exist.")
            current = _validated_receipt_from_row(row)
            if current.execution_reserved:
                raise PermissionError("Live authorization receipt already reserved.")
            if current.execution_performed:
                raise PermissionError("Live authorization receipt already executed.")

            updated = _build_receipt(
                receipt_id=current.receipt_id,
                authorization_id=current.authorization_id,
                actor=current.actor,
                plan_hash=current.plan_hash,
                accepted_revision=current.accepted_revision,
                nonce_hash=current.nonce_hash,
                consumed_at=current.consumed_at,
                execution_reserved=True,
                execution_performed=False,
                repository_snapshot_hash=current.repository_snapshot_hash,
            )
            cursor = connection.execute(
                """
                UPDATE live_authorization_receipts
                SET execution_reserved = 1, record_hash = ?
                WHERE receipt_id = ?
                  AND execution_reserved = 0
                  AND execution_performed = 0
                """,
                (updated.record_hash, receipt_id),
            )
            if cursor.rowcount != 1:
                raise PermissionError("Live authorization receipt already reserved.")
            connection.commit()
        return updated

    def mark_executed(self, receipt_id: str) -> LiveAuthorizationReceipt:
        """Mark one reserved receipt executed exactly once."""

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = _select_receipt(connection, receipt_id)
            if row is None:
                raise PermissionError("Live authorization receipt does not exist.")
            current = _validated_receipt_from_row(row)
            if not current.execution_reserved:
                raise PermissionError(
                    "Live authorization receipt must be reserved before execution."
                )
            if current.execution_performed:
                raise PermissionError("Live authorization receipt already executed.")

            updated = _build_receipt(
                receipt_id=current.receipt_id,
                authorization_id=current.authorization_id,
                actor=current.actor,
                plan_hash=current.plan_hash,
                accepted_revision=current.accepted_revision,
                nonce_hash=current.nonce_hash,
                consumed_at=current.consumed_at,
                execution_reserved=True,
                execution_performed=True,
                repository_snapshot_hash=current.repository_snapshot_hash,
            )
            cursor = connection.execute(
                """
                UPDATE live_authorization_receipts
                SET execution_performed = 1, record_hash = ?
                WHERE receipt_id = ?
                  AND execution_reserved = 1
                  AND execution_performed = 0
                """,
                (updated.record_hash, receipt_id),
            )
            if cursor.rowcount != 1:
                raise PermissionError("Live authorization receipt already executed.")
            connection.commit()
        return updated


def scope_for_live_execution(plan: ExecutionPlan) -> LiveExecutionScope:
    return LiveExecutionScope(
        executable=plan.executable,
        arguments=tuple(plan.arguments),
        working_directory=plan.working_directory,
        environment_names=tuple(plan.environment_names),
        timeout_seconds=plan.timeout_seconds,
        max_output_chars=plan.max_output_chars,
    )


def issue_live_authorization(
    plan: ExecutionPlan,
    snapshot: RepositorySnapshot,
    request: LiveAuthorizationRequest,
    context: LiveAuthorizationContext,
    store: SQLiteLiveAuthorizationStore,
) -> LiveAuthorizationReceipt:
    """Validate, consume, persist, and return one live authorization receipt."""

    reasons: list[str] = []
    if plan.disposition == "deny":
        reasons.append("plan_denied")
    if plan.execution_performed:
        reasons.append("plan_already_executed")
    if request.actor not in context.trusted_actors:
        reasons.append("actor_not_trusted")
    if request.plan_hash != plan.plan_hash:
        reasons.append("plan_hash_mismatch")
    if request.repository_snapshot_hash != snapshot.snapshot_hash:
        reasons.append("repository_snapshot_mismatch")
    if request.scope != scope_for_live_execution(plan):
        reasons.append("authorization_scope_mismatch")
    if request.created_at > context.now:
        reasons.append("authorization_created_in_future")
    if request.expires_at <= context.now:
        reasons.append("authorization_expired")
    if not request.rollback_acknowledged:
        reasons.append("rollback_not_acknowledged")

    plan_root = Path(plan.repository_root).resolve(strict=True)
    snapshot_root = Path(snapshot.repository_root).resolve(strict=True)
    if plan_root != snapshot_root:
        reasons.append("repository_root_mismatch")
    try:
        snapshot.verify_current()
    except PermissionError:
        reasons.append("repository_snapshot_stale")

    nonce_hash = _sha256_text(request.nonce)
    if store.nonce_consumed(nonce_hash):
        reasons.append("nonce_already_consumed")

    if reasons:
        raise PermissionError("Live authorization denied: " + ", ".join(reasons))

    receipt = _build_receipt(
        receipt_id=f"live-receipt-{request.authorization_id}",
        authorization_id=request.authorization_id,
        actor=request.actor,
        plan_hash=request.plan_hash,
        accepted_revision=context.current_revision,
        nonce_hash=nonce_hash,
        consumed_at=context.now,
        execution_reserved=False,
        execution_performed=False,
        repository_snapshot_hash=snapshot.snapshot_hash,
    )
    return store.issue(receipt)


def _select_receipt(
    connection: sqlite3.Connection,
    receipt_id: str,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT receipt_id, authorization_id, actor, plan_hash,
               accepted_revision, nonce_hash, consumed_at,
               execution_reserved, execution_performed,
               repository_snapshot_hash, record_hash
        FROM live_authorization_receipts
        WHERE receipt_id = ?
        """,
        (receipt_id,),
    ).fetchone()


def _validated_receipt_from_row(row: sqlite3.Row) -> LiveAuthorizationReceipt:
    try:
        return _receipt_from_row(row)
    except (ValidationError, ValueError) as exc:
        raise PermissionError(
            "Live authorization receipt integrity verification failed."
        ) from exc


def _build_receipt(
    *,
    receipt_id: str,
    authorization_id: str,
    actor: str,
    plan_hash: str,
    accepted_revision: int,
    nonce_hash: str,
    consumed_at: datetime,
    execution_reserved: bool,
    execution_performed: bool,
    repository_snapshot_hash: str,
) -> LiveAuthorizationReceipt:
    payload = {
        "receipt_id": receipt_id,
        "authorization_id": authorization_id,
        "actor": actor,
        "plan_hash": plan_hash,
        "accepted_revision": accepted_revision,
        "nonce_hash": nonce_hash,
        "consumed_at": consumed_at,
        "execution_reserved": execution_reserved,
        "execution_performed": execution_performed,
        "repository_snapshot_hash": repository_snapshot_hash,
    }
    draft = LiveAuthorizationReceipt.model_construct(record_hash="0" * 64, **payload)
    return LiveAuthorizationReceipt(
        record_hash=draft.calculate_record_hash(),
        **payload,
    )


def _receipt_from_row(row: sqlite3.Row) -> LiveAuthorizationReceipt:
    return LiveAuthorizationReceipt(
        receipt_id=str(row["receipt_id"]),
        authorization_id=str(row["authorization_id"]),
        actor=str(row["actor"]),
        plan_hash=str(row["plan_hash"]),
        accepted_revision=int(row["accepted_revision"]),
        nonce_hash=str(row["nonce_hash"]),
        consumed_at=datetime.fromisoformat(str(row["consumed_at"])),
        execution_reserved=bool(row["execution_reserved"]),
        execution_performed=bool(row["execution_performed"]),
        repository_snapshot_hash=str(row["repository_snapshot_hash"]),
        record_hash=str(row["record_hash"]),
    )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=_json_default,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _json_default(value: object) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object is not JSON serializable: {type(value).__name__}")
