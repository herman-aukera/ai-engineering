"""Restart-persistent ownership for estimator IDs and HITL continuations."""

from __future__ import annotations

from threading import RLock
from typing import Protocol


class EstimationOwnershipError(PermissionError):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


class EstimationOwnershipStore(Protocol):
    restart_persistent: bool

    def setup(self) -> None: ...
    def claim(self, estimation_id: str, owner_id: str) -> None: ...
    def assert_owner(self, estimation_id: str, owner_id: str) -> None: ...
    def close(self) -> None: ...


class InMemoryEstimationOwnershipStore:
    restart_persistent = False

    def __init__(self) -> None:
        self._owners: dict[str, str] = {}
        self._lock = RLock()

    def setup(self) -> None:
        return None

    def claim(self, estimation_id: str, owner_id: str) -> None:
        estimation_id = _identity(estimation_id, "estimation_id", 256)
        owner_id = _identity(owner_id, "owner_id", 256)
        with self._lock:
            existing = self._owners.get(estimation_id)
            if existing is not None and existing != owner_id:
                raise EstimationOwnershipError("tenant_mismatch")
            self._owners[estimation_id] = owner_id

    def assert_owner(self, estimation_id: str, owner_id: str) -> None:
        estimation_id = _identity(estimation_id, "estimation_id", 256)
        owner_id = _identity(owner_id, "owner_id", 256)
        with self._lock:
            existing = self._owners.get(estimation_id)
        if existing is None:
            raise EstimationOwnershipError("resource_owner_missing")
        if existing != owner_id:
            raise EstimationOwnershipError("tenant_mismatch")

    def close(self) -> None:
        return None


class PostgresEstimationOwnershipStore:
    """PostgreSQL-backed owner mapping sharing the estimator's durable DB."""

    restart_persistent = True

    def __init__(
        self,
        connection_string: str,
        *,
        min_size: int = 1,
        max_size: int = 4,
    ) -> None:
        if not connection_string.strip():
            raise ValueError("PostgreSQL ownership storage requires DATABASE_URL")
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        self._pool = ConnectionPool(
            conninfo=connection_string,
            min_size=min_size,
            max_size=max_size,
            kwargs={"autocommit": False, "row_factory": dict_row},
            open=True,
        )
        self._closed = False

    def setup(self) -> None:
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS estimator_resource_owners (
                        estimation_id TEXT PRIMARY KEY,
                        owner_id TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_estimator_resource_owners_owner
                    ON estimator_resource_owners(owner_id)
                    """
                )
            connection.commit()

    def claim(self, estimation_id: str, owner_id: str) -> None:
        estimation_id = _identity(estimation_id, "estimation_id", 256)
        owner_id = _identity(owner_id, "owner_id", 256)
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO estimator_resource_owners(estimation_id, owner_id)
                    VALUES (%s, %s)
                    ON CONFLICT (estimation_id) DO NOTHING
                    """,
                    (estimation_id, owner_id),
                )
                cursor.execute(
                    """
                    SELECT owner_id FROM estimator_resource_owners
                    WHERE estimation_id = %s
                    FOR UPDATE
                    """,
                    (estimation_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError("estimation ownership claim was not persisted")
                if str(row["owner_id"]) != owner_id:
                    raise EstimationOwnershipError("tenant_mismatch")
            connection.commit()

    def assert_owner(self, estimation_id: str, owner_id: str) -> None:
        estimation_id = _identity(estimation_id, "estimation_id", 256)
        owner_id = _identity(owner_id, "owner_id", 256)
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT owner_id FROM estimator_resource_owners
                    WHERE estimation_id = %s
                    """,
                    (estimation_id,),
                )
                row = cursor.fetchone()
        if row is None:
            raise EstimationOwnershipError("resource_owner_missing")
        if str(row["owner_id"]) != owner_id:
            raise EstimationOwnershipError("tenant_mismatch")

    def close(self) -> None:
        if not self._closed:
            self._pool.close()
            self._closed = True


def _identity(value: str, field: str, maximum: int) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{field} must contain between 1 and {maximum} characters")
    return normalized
