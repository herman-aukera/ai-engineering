from __future__ import annotations

from datetime import UTC, datetime

from app.energy_chat.contracts import ProjectRagRequest
from app.energy_chat.support_pgvector import (
    RETRIEVAL_STRATEGY,
    PgvectorSupportRagService,
    _vector_literal,
)
from app.energy_chat.support_rag import SupportChunk


class FakeEmbeddingProvider:
    model = "fake-embedding-v1"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, float("postgres" in text.casefold())] for text in texts]


class FakePgvectorStore:
    backend_name = "postgresql_pgvector_hnsw"

    def __init__(self) -> None:
        self.setup_called = False
        self.search_called = False
        self.chunk = SupportChunk(
            chunk_id="chunk-1",
            source_id="postgres_connections",
            source_family="postgresql",
            product="PostgreSQL",
            product_version="current",
            title="PostgreSQL connections",
            canonical_url="https://www.postgresql.org/docs/current/runtime-config-connection.html",
            support_categories=("database_connections",),
            section="Connections",
            content="PostgreSQL connection limits constrain concurrent sessions.",
            content_hash="hash",
            ingestion_version="test",
            retrieved_at=datetime.now(UTC),
            embedding_model="fake-embedding-v1",
            embedding=(1.0, 1.0),
        )

    def setup(self) -> None:
        self.setup_called = True

    def count_active_chunks(self) -> int:
        return 1

    def search(self, query_embedding: list[float], k: int):
        self.search_called = True
        assert query_embedding == [1.0, 1.0]
        assert k == 1
        return [(0.97, self.chunk)]


def test_pgvector_service_uses_store_native_search_contract() -> None:
    store = FakePgvectorStore()
    service = PgvectorSupportRagService(store=store, embeddings=FakeEmbeddingProvider())  # type: ignore[arg-type]

    result = service.retrieve(ProjectRagRequest(query="Postgres connection limit", k=1))

    assert store.setup_called is True
    assert store.search_called is True
    assert result.retrieval_strategy == RETRIEVAL_STRATEGY
    assert result.results[0].source_id == "postgres_connections"
    assert result.results[0].evidence_ref.startswith("source:postgres_connections:")
    assert "pgvector" in result.grounding_summary


def test_pgvector_literal_is_stable_and_database_compatible() -> None:
    assert _vector_literal([1.0, 0.25, -2.0]) == "[1,0.25,-2]"
