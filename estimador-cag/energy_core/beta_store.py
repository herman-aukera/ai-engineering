"""SQLite persistence and one-time authorization receipts for the EACODE beta API."""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from energy_core.beta_demo import BetaDemoResult
from energy_core.models import EnergyModel


class DemoAuthorizationReceipt(EnergyModel):
    schema_version: str = "1.0.0"
    receipt_id: str = Field(min_length=20, max_length=200)
    proposal_id: str = Field(min_length=1, max_length=200)
    actor: str = Field(min_length=1, max_length=240)
    scope_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    nonce_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    issued_at: datetime
    expires_at: datetime
    consumed_at: datetime | None = None
    record_hash: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_receipt(self) -> DemoAuthorizationReceipt:
        for name in ("issued_at", "expires_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.consumed_at is not None and (
            self.consumed_at.tzinfo is None or self.consumed_at.utcoffset() is None
        ):
            raise ValueError("consumed_at must be timezone-aware")
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be later than issued_at")
        if self.record_hash != self.calculate_record_hash():
            raise ValueError("record_hash does not match authorization receipt")
        return self

    def calculate_record_hash(self) -> str:
        return _sha256_json(self.model_dump(mode="json", exclude={"record_hash"}))


class SQLiteBetaDemoStore:
    """Durable beta records with integrity checking and atomic receipt consumption."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path).expanduser().resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._setup()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def _setup(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS beta_demo_runs (
                    proposal_id TEXT PRIMARY KEY,
                    result_json TEXT NOT NULL,
                    result_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS beta_demo_authorizations (
                    receipt_id TEXT PRIMARY KEY,
                    proposal_id TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    scope_hash TEXT NOT NULL,
                    nonce_hash TEXT NOT NULL UNIQUE,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    consumed_at TEXT,
                    record_hash TEXT NOT NULL,
                    FOREIGN KEY (proposal_id)
                        REFERENCES beta_demo_runs(proposal_id)
                        ON DELETE RESTRICT
                )
                """
            )
            connection.commit()

    def create_result(self, result: BetaDemoResult, *, now: datetime | None = None) -> None:
        timestamp = _aware_now(now)
        payload = result.model_dump(mode="json")
        encoded = _canonical_json(payload)
        digest = _sha256_text(encoded)
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    INSERT INTO beta_demo_runs (
                        proposal_id, result_json, result_hash, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        result.proposal.proposal_id,
                        encoded,
                        digest,
                        timestamp.isoformat(),
                        timestamp.isoformat(),
                    ),
                )
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise FileExistsError(
                f"Demo proposal already exists: {result.proposal.proposal_id}"
            ) from exc

    def update_result(self, result: BetaDemoResult, *, now: datetime | None = None) -> None:
        timestamp = _aware_now(now)
        encoded = _canonical_json(result.model_dump(mode="json"))
        digest = _sha256_text(encoded)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                UPDATE beta_demo_runs
                SET result_json = ?, result_hash = ?, updated_at = ?
                WHERE proposal_id = ?
                """,
                (
                    encoded,
                    digest,
                    timestamp.isoformat(),
                    result.proposal.proposal_id,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError(result.proposal.proposal_id)
            connection.commit()

    def get_result(self, proposal_id: str) -> BetaDemoResult | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT result_json, result_hash
                FROM beta_demo_runs
                WHERE proposal_id = ?
                """,
                (proposal_id,),
            ).fetchone()
        if row is None:
            return None
        encoded = str(row["result_json"])
        if _sha256_text(encoded) != str(row["result_hash"]):
            raise PermissionError("Demo result integrity verification failed.")
        try:
            return BetaDemoResult.model_validate_json(encoded)
        except ValueError as exc:
            raise PermissionError("Demo result schema verification failed.") from exc

    def issue_authorization(
        self,
        *,
        proposal_id: str,
        actor: str,
        scope: tuple[tuple[str, ...], ...],
        now: datetime | None = None,
        ttl_seconds: int = 300,
    ) -> DemoAuthorizationReceipt:
        if ttl_seconds < 1 or ttl_seconds > 900:
            raise ValueError("ttl_seconds must be between 1 and 900")
        if self.get_result(proposal_id) is None:
            raise KeyError(proposal_id)

        issued_at = _aware_now(now)
        expires_at = issued_at + timedelta(seconds=ttl_seconds)
        nonce_hash = _sha256_text(secrets.token_urlsafe(32))
        receipt_id = f"demo-receipt-{secrets.token_urlsafe(24)}"
        receipt = _build_receipt(
            receipt_id=receipt_id,
            proposal_id=proposal_id,
            actor=actor,
            scope_hash=scope_hash(scope),
            nonce_hash=nonce_hash,
            issued_at=issued_at,
            expires_at=expires_at,
            consumed_at=None,
        )
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    INSERT INTO beta_demo_authorizations (
                        receipt_id, proposal_id, actor, scope_hash, nonce_hash,
                        issued_at, expires_at, consumed_at, record_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        receipt.receipt_id,
                        receipt.proposal_id,
                        receipt.actor,
                        receipt.scope_hash,
                        receipt.nonce_hash,
                        receipt.issued_at.isoformat(),
                        receipt.expires_at.isoformat(),
                        None,
                        receipt.record_hash,
                    ),
                )
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise PermissionError("Authorization receipt collision or replay detected.") from exc
        return receipt

    def consume_authorization(
        self,
        *,
        receipt_id: str,
        proposal_id: str,
        actor: str,
        scope: tuple[tuple[str, ...], ...],
        now: datetime | None = None,
    ) -> DemoAuthorizationReceipt:
        consumed_at = _aware_now(now)
        expected_scope_hash = scope_hash(scope)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT receipt_id, proposal_id, actor, scope_hash, nonce_hash,
                       issued_at, expires_at, consumed_at, record_hash
                FROM beta_demo_authorizations
                WHERE receipt_id = ?
                """,
                (receipt_id,),
            ).fetchone()
            if row is None:
                raise PermissionError("Authorization receipt does not exist.")
            current = _receipt_from_row(row)
            reasons: list[str] = []
            if current.proposal_id != proposal_id:
                reasons.append("proposal_mismatch")
            if current.actor != actor:
                reasons.append("actor_mismatch")
            if current.scope_hash != expected_scope_hash:
                reasons.append("scope_mismatch")
            if current.consumed_at is not None:
                reasons.append("receipt_already_consumed")
            if current.expires_at <= consumed_at:
                reasons.append("receipt_expired")
            if current.issued_at > consumed_at:
                reasons.append("receipt_issued_in_future")
            if reasons:
                raise PermissionError(
                    "Authorization receipt denied: " + ", ".join(reasons)
                )

            consumed = _build_receipt(
                receipt_id=current.receipt_id,
                proposal_id=current.proposal_id,
                actor=current.actor,
                scope_hash=current.scope_hash,
                nonce_hash=current.nonce_hash,
                issued_at=current.issued_at,
                expires_at=current.expires_at,
                consumed_at=consumed_at,
            )
            cursor = connection.execute(
                """
                UPDATE beta_demo_authorizations
                SET consumed_at = ?, record_hash = ?
                WHERE receipt_id = ? AND consumed_at IS NULL
                """,
                (
                    consumed.consumed_at.isoformat(),
                    consumed.record_hash,
                    receipt_id,
                ),
            )
            if cursor.rowcount != 1:
                raise PermissionError("Authorization receipt was consumed concurrently.")
            connection.commit()
        return consumed

    def get_authorization(self, receipt_id: str) -> DemoAuthorizationReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT receipt_id, proposal_id, actor, scope_hash, nonce_hash,
                       issued_at, expires_at, consumed_at, record_hash
                FROM beta_demo_authorizations
                WHERE receipt_id = ?
                """,
                (receipt_id,),
            ).fetchone()
        return None if row is None else _receipt_from_row(row)


def scope_hash(scope: tuple[tuple[str, ...], ...]) -> str:
    return _sha256_json([list(command) for command in scope])


def _receipt_from_row(row: sqlite3.Row) -> DemoAuthorizationReceipt:
    try:
        return DemoAuthorizationReceipt(
            receipt_id=str(row["receipt_id"]),
            proposal_id=str(row["proposal_id"]),
            actor=str(row["actor"]),
            scope_hash=str(row["scope_hash"]),
            nonce_hash=str(row["nonce_hash"]),
            issued_at=datetime.fromisoformat(str(row["issued_at"])),
            expires_at=datetime.fromisoformat(str(row["expires_at"])),
            consumed_at=(
                datetime.fromisoformat(str(row["consumed_at"]))
                if row["consumed_at"] is not None
                else None
            ),
            record_hash=str(row["record_hash"]),
        )
    except ValueError as exc:
        raise PermissionError("Authorization receipt integrity verification failed.") from exc


def _build_receipt(
    *,
    receipt_id: str,
    proposal_id: str,
    actor: str,
    scope_hash: str,
    nonce_hash: str,
    issued_at: datetime,
    expires_at: datetime,
    consumed_at: datetime | None,
) -> DemoAuthorizationReceipt:
    payload = {
        "receipt_id": receipt_id,
        "proposal_id": proposal_id,
        "actor": actor,
        "scope_hash": scope_hash,
        "nonce_hash": nonce_hash,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "consumed_at": consumed_at,
    }
    draft = DemoAuthorizationReceipt.model_construct(
        record_hash="0" * 64,
        **payload,
    )
    return DemoAuthorizationReceipt(
        record_hash=draft.calculate_record_hash(),
        **payload,
    )


def _aware_now(value: datetime | None) -> datetime:
    result = value or datetime.now(UTC)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    return result


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=_json_default,
    )


def _sha256_json(payload: object) -> str:
    return _sha256_text(_canonical_json(payload))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _json_default(value: object) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object is not JSON serializable: {type(value).__name__}")
