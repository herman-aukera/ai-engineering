"""Durable resource ownership for EACHAT conversations and graph threads."""

from __future__ import annotations

from threading import RLock
from typing import Protocol


class ResourceOwnershipError(PermissionError):
    """Stable ownership rejection with a machine-readable reason code."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


class ResourceOwnershipStore(Protocol):
    restart_persistent: bool

    def setup(self) -> None: ...
    def ping(self) -> bool: ...
    def claim(self, resource_type: str, resource_id: str, owner_id: str) -> None: ...
    def assert_owner(self, resource_type: str, resource_id: str, owner_id: str) -> None: ...
    def delete(self, resource_type: str, resource_id: str, owner_id: str) -> None: ...
    def close(self) -> None: ...


class InMemoryResourceOwnershipStore:
    restart_persistent = False

    def __init__(self) -> None:
        self._owners: dict[tuple[str, str], str] = {}
        self._lock = RLock()

    def setup(self) -> None:
        return None

    def ping(self) -> bool:
        return True

    def claim(self, resource_type: str, resource_id: str, owner_id: str) -> None:
        key = _key(resource_type, resource_id)
        owner_id = _owner(owner_id)
        with self._lock:
            existing = self._owners.get(key)
            if existing is not None and existing != owner_id:
                raise ResourceOwnershipError("tenant_mismatch")
            self._owners[key] = owner_id

    def assert_owner(self, resource_type: str, resource_id: str, owner_id: str) -> None:
        key = _key(resource_type, resource_id)
        owner_id = _owner(owner_id)
        with self._lock:
            existing = self._owners.get(key)
        if existing is None:
            raise ResourceOwnershipError("resource_owner_missing")
        if existing != owner_id:
            raise ResourceOwnershipError("tenant_mismatch")

    def delete(self, resource_type: str, resource_id: str, owner_id: str) -> None:
        key = _key(resource_type, resource_id)
        self.assert_owner(resource_type, resource_id, owner_id)
        with self._lock:
            self._owners.pop(key, None)

    def close(self) -> None:
        return None


class PostgresResourceOwnershipStore:
    """PostgreSQL-backed ownership that survives replaceable application compute."""

    restart_persistent = True

    def __init__(
        self,
        connection_string: str,
        *,
        min_size: int = 1,
        max_size: int = 4,
    ) -> None:
        if not connection_string.strip():
            raise ValueError("PostgreSQL ownership storage requires a connection string")
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        self._pool = ConnectionPool(
            conninfo=connection_string,
            min_size=min_size,
            max_size=max_size,
            timeout=2.0,
            kwargs={
                "autocommit": False,
                "row_factory": dict_row,
                "connect_timeout": 2,
            },
            open=True,
        )
        self._closed = False

    def setup(self) -> None:
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS eachat_resource_owners (
                        resource_type TEXT NOT NULL,
                        resource_id TEXT NOT NULL,
                        owner_id TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        PRIMARY KEY (resource_type, resource_id)
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_eachat_resource_owners_owner
                    ON eachat_resource_owners(owner_id)
                    """
                )
            connection.commit()

    def ping(self) -> bool:
        if self._closed:
            return False
        try:
            with self._pool.connection(timeout=2.0) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    row = cursor.fetchone()
            if isinstance(row, dict):
                return next(iter(row.values()), None) == 1
            return bool(row and row[0] == 1)
        except Exception:
            return False

    def claim(self, resource_type: str, resource_id: str, owner_id: str) -> None:
        resource_type, resource_id = _key(resource_type, resource_id)
        owner_id = _owner(owner_id)
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO eachat_resource_owners(resource_type, resource_id, owner_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (resource_type, resource_id) DO NOTHING
                    """,
                    (resource_type, resource_id, owner_id),
                )
                cursor.execute(
                    """
                    SELECT owner_id FROM eachat_resource_owners
                    WHERE resource_type = %s AND resource_id = %s
                    FOR UPDATE
                    """,
                    (resource_type, resource_id),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError("resource ownership claim was not persisted")
                if str(row["owner_id"]) != owner_id:
                    raise ResourceOwnershipError("tenant_mismatch")
            connection.commit()

    def assert_owner(self, resource_type: str, resource_id: str, owner_id: str) -> None:
        resource_type, resource_id = _key(resource_type, resource_id)
        owner_id = _owner(owner_id)
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT owner_id FROM eachat_resource_owners
                    WHERE resource_type = %s AND resource_id = %s
                    """,
                    (resource_type, resource_id),
                )
                row = cursor.fetchone()
        if row is None:
            raise ResourceOwnershipError("resource_owner_missing")
        if str(row["owner_id"]) != owner_id:
            raise ResourceOwnershipError("tenant_mismatch")

    def delete(self, resource_type: str, resource_id: str, owner_id: str) -> None:
        resource_type, resource_id = _key(resource_type, resource_id)
        owner_id = _owner(owner_id)
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM eachat_resource_owners
                    WHERE resource_type = %s AND resource_id = %s AND owner_id = %s
                    """,
                    (resource_type, resource_id, owner_id),
                )
                deleted = cursor.rowcount
            connection.commit()
        if deleted != 1:
            self.assert_owner(resource_type, resource_id, owner_id)
            raise ResourceOwnershipError("resource_owner_missing")

    def close(self) -> None:
        if not self._closed:
            self._pool.close()
            self._closed = True


def _key(resource_type: str, resource_id: str) -> tuple[str, str]:
    resource_type = resource_type.strip()
    resource_id = resource_id.strip()
    if not resource_type or len(resource_type) > 64:
        raise ValueError("resource_type must contain between 1 and 64 characters")
    if not resource_id or len(resource_id) > 256:
        raise ValueError("resource_id must contain between 1 and 256 characters")
    return resource_type, resource_id


def _owner(owner_id: str) -> str:
    normalized = owner_id.strip()
    if not normalized or len(normalized) > 256:
        raise ValueError("owner_id must contain between 1 and 256 characters")
    return normalized
