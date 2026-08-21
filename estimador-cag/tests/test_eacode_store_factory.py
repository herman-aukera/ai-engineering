import pytest

from energy_core.beta_store import SQLiteBetaDemoStore
from energy_core.beta_store_runtime import build_beta_demo_store
from energy_core.postgres_beta_store import PostgresBetaDemoStore


def test_production_authority_store_fails_closed_without_postgres(monkeypatch) -> None:
    monkeypatch.delenv("EACODE_DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="EACODE_DATABASE_URL"):
        build_beta_demo_store(require_durable=True)


def test_database_url_selects_postgres_authority_store(monkeypatch) -> None:
    monkeypatch.setenv("EACODE_DATABASE_URL", "postgresql://user:pass@example/db")

    store = build_beta_demo_store(require_durable=True)

    assert isinstance(store, PostgresBetaDemoStore)


def test_sqlite_remains_compatibility_only_for_local_and_tests(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("EACODE_DATABASE_URL", raising=False)
    monkeypatch.setenv("EACODE_DEMO_DB_PATH", str(tmp_path / "compat.sqlite3"))

    store = build_beta_demo_store(require_durable=False)

    assert isinstance(store, SQLiteBetaDemoStore)
