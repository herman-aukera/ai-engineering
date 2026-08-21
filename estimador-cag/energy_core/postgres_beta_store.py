"""PostgreSQL authority store for the EACODE governed beta lifecycle."""

from __future__ import annotations

import argparse
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2 import IntegrityError
from psycopg2.extras import RealDictCursor

from energy_core.beta_demo import BetaDemoResult
from energy_core.beta_store import (
    DemoAuthorizationReceipt,
    _aware_now,
    _build_receipt,
    _canonical_json,
    _sha256_text,
    _validate_owner,
    scope_hash,
)

SCHEMA_VERSION = "0001_eacode_beta_authority"
MIGRATION_PATH = (
    Path(__file__).resolve().parent
    / "migrations"
    / "0001_eacode_beta_authority.sql"
)


class PostgresBetaDemoStore:
    """Tenant-scoped durable authority with transactional one-time execution."""

    schema_version = SCHEMA_VERSION

    def __init__(self, database_url: str) -> None:
        normalized = database_url.strip()
        if not normalized:
            raise ValueError("EACODE_DATABASE_URL must not be blank")
        self.database_url = normalized

    def _connect(self):
        return psycopg2.connect(
            self.database_url,
            connect_timeout=5,
            cursor_factory=RealDictCursor,
        )

    def verify_schema(self) -> None:
        """Fail closed unless the expected versioned schema is already applied."""

        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    "SELECT version FROM eacode_schema_migrations WHERE version = %s",
                    (SCHEMA_VERSION,),
                )
                version = cursor.fetchone()
                cursor.execute("SELECT 1 FROM eacode_beta_demo_runs LIMIT 1")
                cursor.execute("SELECT 1 FROM eacode_beta_demo_authorizations LIMIT 1")
        except psycopg2.Error as exc:
            raise RuntimeError("EACODE PostgreSQL authority schema is unavailable") from exc
        if version is None:
            raise RuntimeError(
                f"EACODE PostgreSQL authority schema {SCHEMA_VERSION} is not applied"
            )

    def create_result(
        self,
        result: BetaDemoResult,
        *,
        owner_id: str,
        now: datetime | None = None,
    ) -> None:
        _validate_owner(owner_id)
        timestamp = _aware_now(now)
        encoded = _canonical_json(result.model_dump(mode="json"))
        digest = _sha256_text(encoded)
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO eacode_beta_demo_runs (
                        proposal_id, owner_id, result_json, result_hash,
                        execution_reserved, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, FALSE, %s, %s)
                    """,
                    (
                        result.proposal.proposal_id,
                        owner_id,
                        encoded,
                        digest,
                        timestamp,
                        timestamp,
                    ),
                )
        except IntegrityError as exc:
            raise FileExistsError(
                f"Demo proposal already exists: {result.proposal.proposal_id}"
            ) from exc

    def update_result(
        self,
        result: BetaDemoResult,
        *,
        owner_id: str | None,
        now: datetime | None = None,
    ) -> None:
        timestamp = _aware_now(now)
        encoded = _canonical_json(result.model_dump(mode="json"))
        digest = _sha256_text(encoded)
        with self._connect() as connection, connection.cursor() as cursor:
            if owner_id is None:
                cursor.execute(
                    """
                    UPDATE eacode_beta_demo_runs
                    SET result_json = %s, result_hash = %s, updated_at = %s
                    WHERE proposal_id = %s AND execution_reserved = TRUE
                    """,
                    (encoded, digest, timestamp, result.proposal.proposal_id),
                )
            else:
                _validate_owner(owner_id)
                cursor.execute(
                    """
                    UPDATE eacode_beta_demo_runs
                    SET result_json = %s, result_hash = %s, updated_at = %s
                    WHERE proposal_id = %s AND owner_id = %s
                      AND execution_reserved = TRUE
                    """,
                    (
                        encoded,
                        digest,
                        timestamp,
                        result.proposal.proposal_id,
                        owner_id,
                    ),
                )
            if cursor.rowcount != 1:
                raise PermissionError(
                    "Demo result update denied or execution was not reserved."
                )

    def get_result(
        self,
        proposal_id: str,
        *,
        owner_id: str | None,
    ) -> BetaDemoResult | None:
        with self._connect() as connection, connection.cursor() as cursor:
            if owner_id is None:
                cursor.execute(
                    """
                    SELECT result_json, result_hash
                    FROM eacode_beta_demo_runs
                    WHERE proposal_id = %s
                    """,
                    (proposal_id,),
                )
            else:
                _validate_owner(owner_id)
                cursor.execute(
                    """
                    SELECT result_json, result_hash
                    FROM eacode_beta_demo_runs
                    WHERE proposal_id = %s AND owner_id = %s
                    """,
                    (proposal_id, owner_id),
                )
            row = cursor.fetchone()
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
        owner_id: str | None,
        scope: tuple[tuple[str, ...], ...],
        now: datetime | None = None,
        ttl_seconds: int = 300,
    ) -> DemoAuthorizationReceipt:
        if ttl_seconds < 1 or ttl_seconds > 900:
            raise ValueError("ttl_seconds must be between 1 and 900")
        _validate_owner(actor)
        if owner_id is not None:
            _validate_owner(owner_id)

        issued_at = _aware_now(now)
        receipt = _build_receipt(
            receipt_id=f"demo-receipt-{secrets.token_urlsafe(24)}",
            proposal_id=proposal_id,
            actor=actor,
            scope_hash=scope_hash(scope),
            nonce_hash=_sha256_text(secrets.token_urlsafe(32)),
            issued_at=issued_at,
            expires_at=issued_at + timedelta(seconds=ttl_seconds),
            consumed_at=None,
        )
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                run = self._select_run(cursor, proposal_id, for_update=True)
                self._verify_run_access(run, owner_id)
                if bool(run["execution_reserved"]):
                    raise PermissionError("Demo execution is already reserved.")
                cursor.execute(
                    """
                    INSERT INTO eacode_beta_demo_authorizations (
                        receipt_id, proposal_id, actor, scope_hash, nonce_hash,
                        issued_at, expires_at, consumed_at, record_hash
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        receipt.receipt_id,
                        receipt.proposal_id,
                        receipt.actor,
                        receipt.scope_hash,
                        receipt.nonce_hash,
                        receipt.issued_at,
                        receipt.expires_at,
                        None,
                        receipt.record_hash,
                    ),
                )
        except IntegrityError as exc:
            raise PermissionError("Authorization receipt collision or replay detected.") from exc
        return receipt

    def consume_authorization(
        self,
        *,
        receipt_id: str,
        proposal_id: str,
        actor: str,
        owner_id: str | None,
        scope: tuple[tuple[str, ...], ...],
        now: datetime | None = None,
    ) -> DemoAuthorizationReceipt:
        consumed_at = _aware_now(now)
        expected_scope_hash = scope_hash(scope)
        with self._connect() as connection, connection.cursor() as cursor:
            run = self._select_run(cursor, proposal_id, for_update=True)
            self._verify_run_access(run, owner_id)
            cursor.execute(
                """
                SELECT receipt_id, proposal_id, actor, scope_hash, nonce_hash,
                       issued_at, expires_at, consumed_at, record_hash
                FROM eacode_beta_demo_authorizations
                WHERE receipt_id = %s
                FOR UPDATE
                """,
                (receipt_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise PermissionError("Authorization receipt does not exist.")
            current = _receipt_from_mapping(row)
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
            if bool(run["execution_reserved"]):
                reasons.append("execution_already_reserved")
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
            cursor.execute(
                """
                UPDATE eacode_beta_demo_runs
                SET execution_reserved = TRUE, updated_at = %s
                WHERE proposal_id = %s AND execution_reserved = FALSE
                """,
                (consumed_at, proposal_id),
            )
            if cursor.rowcount != 1:
                raise PermissionError("Demo execution was reserved concurrently.")
            cursor.execute(
                """
                UPDATE eacode_beta_demo_authorizations
                SET consumed_at = %s, record_hash = %s
                WHERE receipt_id = %s AND consumed_at IS NULL
                """,
                (consumed.consumed_at, consumed.record_hash, receipt_id),
            )
            if cursor.rowcount != 1:
                raise PermissionError("Authorization receipt was consumed concurrently.")
        return consumed

    def get_authorization(self, receipt_id: str) -> DemoAuthorizationReceipt | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT receipt_id, proposal_id, actor, scope_hash, nonce_hash,
                       issued_at, expires_at, consumed_at, record_hash
                FROM eacode_beta_demo_authorizations
                WHERE receipt_id = %s
                """,
                (receipt_id,),
            )
            row = cursor.fetchone()
        return None if row is None else _receipt_from_mapping(row)

    @staticmethod
    def _verify_run_access(run: dict[str, Any], owner_id: str | None) -> None:
        if owner_id is not None and str(run["owner_id"]) != owner_id:
            raise PermissionError("Demo proposal is not accessible to this session.")

    @staticmethod
    def _select_run(cursor, proposal_id: str, *, for_update: bool) -> dict[str, Any]:
        suffix = " FOR UPDATE" if for_update else ""
        cursor.execute(
            """
            SELECT proposal_id, owner_id, execution_reserved
            FROM eacode_beta_demo_runs
            WHERE proposal_id = %s
            """ + suffix,
            (proposal_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise KeyError(proposal_id)
        return row


def _as_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _receipt_from_mapping(row: dict[str, Any]) -> DemoAuthorizationReceipt:
    try:
        return DemoAuthorizationReceipt(
            receipt_id=str(row["receipt_id"]),
            proposal_id=str(row["proposal_id"]),
            actor=str(row["actor"]),
            scope_hash=str(row["scope_hash"]),
            nonce_hash=str(row["nonce_hash"]),
            issued_at=_as_datetime(row["issued_at"]),
            expires_at=_as_datetime(row["expires_at"]),
            consumed_at=(
                _as_datetime(row["consumed_at"])
                if row["consumed_at"] is not None
                else None
            ),
            record_hash=str(row["record_hash"]),
        )
    except ValueError as exc:
        raise PermissionError("Authorization receipt integrity verification failed.") from exc


def migrate_database(database_url: str) -> None:
    """Apply the explicit additive authority schema migration."""

    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    with psycopg2.connect(database_url, connect_timeout=5) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)


def main() -> None:
    parser = argparse.ArgumentParser(description="EACODE authority-store migration tool")
    parser.add_argument("action", choices=("migrate", "verify"))
    args = parser.parse_args()
    database_url = os.getenv("EACODE_DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("EACODE_DATABASE_URL is required")
    if args.action == "migrate":
        migrate_database(database_url)
        print(f"EACODE migration applied: {SCHEMA_VERSION}")
    else:
        PostgresBetaDemoStore(database_url).verify_schema()
        print(f"EACODE schema verified: {SCHEMA_VERSION}")


if __name__ == "__main__":
    main()
