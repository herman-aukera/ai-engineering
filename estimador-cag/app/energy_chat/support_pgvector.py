"""PostgreSQL + pgvector backend for the EACHAT final-project support RAG."""

from __future__ import annotations

import json
import os
from functools import lru_cache

from app.energy_chat.contracts import ProjectRagChunk, ProjectRagRequest, ProjectRagResult
from app.energy_chat.support_rag import (
    DEFAULT_EMBEDDING_MODEL,
    OpenAIEmbeddingProvider,
    SupportChunk,
    SupportRagService,
    SupportRagUnavailableError,
)

DEFAULT_EMBEDDING_DIMENSIONS = 1536
RETRIEVAL_STRATEGY = "openai_embedding_postgres_pgvector_cosine_support_rag"


class PgvectorSupportRagStore:
    """Persistent support corpus with native pgvector storage and HNSW indexing."""

    backend_name = "postgresql_pgvector_hnsw"

    def __init__(self, connection_string: str, *, embedding_dimensions: int = 1536) -> None:
        if not connection_string.strip():
            raise SupportRagUnavailableError(
                "EACHAT support RAG requires EACHAT_SUPPORT_RAG_DATABASE_URL "
                "or EACHAT_POSTGRES_URL."
            )
        if embedding_dimensions <= 0:
            raise ValueError("embedding_dimensions must be positive")
        self._connection_string = connection_string
        self._embedding_dimensions = embedding_dimensions

    def _connect(self):
        from psycopg import connect
        from psycopg.rows import dict_row

        return connect(self._connection_string, row_factory=dict_row)

    def setup(self) -> None:
        statements = (
            "CREATE EXTENSION IF NOT EXISTS vector",
            f"""
            CREATE TABLE IF NOT EXISTS eachat_support_pgvector_chunks (
                chunk_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                source_family TEXT NOT NULL,
                product TEXT NOT NULL,
                product_version TEXT NOT NULL,
                title TEXT NOT NULL,
                canonical_url TEXT NOT NULL,
                support_categories JSONB NOT NULL,
                section TEXT NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                ingestion_version TEXT NOT NULL,
                retrieved_at TIMESTAMPTZ NOT NULL,
                embedding_model TEXT NOT NULL,
                embedding VECTOR({self._embedding_dimensions}) NOT NULL,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_eachat_support_pgvector_source
            ON eachat_support_pgvector_chunks (source_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_eachat_support_pgvector_family
            ON eachat_support_pgvector_chunks (active, source_family)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_eachat_support_pgvector_hnsw
            ON eachat_support_pgvector_chunks USING hnsw (embedding vector_cosine_ops)
            WHERE active = TRUE
            """,
        )
        with self._connect() as connection:
            for statement in statements:
                connection.execute(statement)

    def replace_source_chunks(self, source_id: str, chunks: list[SupportChunk]) -> None:
        for chunk in chunks:
            if len(chunk.embedding) != self._embedding_dimensions:
                raise ValueError(
                    "Embedding dimension does not match pgvector configuration: "
                    f"expected {self._embedding_dimensions}, got {len(chunk.embedding)}"
                )
        with self._connect() as connection:
            connection.execute(
                "UPDATE eachat_support_pgvector_chunks SET active = FALSE, updated_at = NOW() "
                "WHERE source_id = %s",
                (source_id,),
            )
            for chunk in chunks:
                connection.execute(
                    """
                    INSERT INTO eachat_support_pgvector_chunks (
                        chunk_id, source_id, source_family, product, product_version,
                        title, canonical_url, support_categories, section, content,
                        content_hash, ingestion_version, retrieved_at, embedding_model,
                        embedding, active, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s,
                        %s, %s, %s, %s, %s::vector, TRUE, NOW()
                    )
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        source_family = EXCLUDED.source_family,
                        product = EXCLUDED.product,
                        product_version = EXCLUDED.product_version,
                        title = EXCLUDED.title,
                        canonical_url = EXCLUDED.canonical_url,
                        support_categories = EXCLUDED.support_categories,
                        section = EXCLUDED.section,
                        content = EXCLUDED.content,
                        content_hash = EXCLUDED.content_hash,
                        ingestion_version = EXCLUDED.ingestion_version,
                        retrieved_at = EXCLUDED.retrieved_at,
                        embedding_model = EXCLUDED.embedding_model,
                        embedding = EXCLUDED.embedding,
                        active = TRUE,
                        updated_at = NOW()
                    """,
                    (
                        chunk.chunk_id,
                        chunk.source_id,
                        chunk.source_family,
                        chunk.product,
                        chunk.product_version,
                        chunk.title,
                        chunk.canonical_url,
                        json.dumps(list(chunk.support_categories)),
                        chunk.section,
                        chunk.content,
                        chunk.content_hash,
                        chunk.ingestion_version,
                        chunk.retrieved_at,
                        chunk.embedding_model,
                        _vector_literal(chunk.embedding),
                    ),
                )

    def list_active_chunks(self) -> list[SupportChunk]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT chunk_id, source_id, source_family, product, product_version,
                       title, canonical_url, support_categories::text AS support_categories,
                       section, content, content_hash, ingestion_version, retrieved_at,
                       embedding_model, embedding::text AS embedding
                FROM eachat_support_pgvector_chunks
                WHERE active = TRUE
                ORDER BY chunk_id
                """
            ).fetchall()
        return [_row_to_chunk(row) for row in rows]

    def count_active_chunks(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM eachat_support_pgvector_chunks WHERE active = TRUE"
            ).fetchone()
        return int(row["count"])

    def search(self, query_embedding: list[float], k: int) -> list[tuple[float, SupportChunk]]:
        if len(query_embedding) != self._embedding_dimensions:
            raise ValueError(
                "Query embedding dimension does not match pgvector configuration: "
                f"expected {self._embedding_dimensions}, got {len(query_embedding)}"
            )
        vector = _vector_literal(query_embedding)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT chunk_id, source_id, source_family, product, product_version,
                       title, canonical_url, support_categories::text AS support_categories,
                       section, content, content_hash, ingestion_version, retrieved_at,
                       embedding_model, embedding::text AS embedding,
                       1 - (embedding <=> %s::vector) AS cosine_score
                FROM eachat_support_pgvector_chunks
                WHERE active = TRUE
                ORDER BY embedding <=> %s::vector, chunk_id
                LIMIT %s
                """,
                (vector, vector, k),
            ).fetchall()
        return [(float(row["cosine_score"]), _row_to_chunk(row)) for row in rows]


class PgvectorSupportRagService(SupportRagService):
    """Support RAG service whose query path executes inside pgvector."""

    store: PgvectorSupportRagStore

    def ingest_manifest(self, *args, **kwargs) -> dict[str, object]:
        report = super().ingest_manifest(*args, **kwargs)
        return {**report, "vector_backend": self.store.backend_name}

    def retrieve(self, request: ProjectRagRequest) -> ProjectRagResult:
        self.store.setup()
        if self.store.count_active_chunks() == 0:
            raise SupportRagUnavailableError(
                "EACHAT support RAG contains no active chunks. Run the support ingestion command first."
            )
        query_vector = self.embeddings.embed_texts([request.query])[0]
        selected = self.store.search(query_vector, request.k)
        results = [
            ProjectRagChunk(
                source_id=chunk.source_id,
                title=f"{chunk.title} — {chunk.section}",
                content=chunk.content,
                evidence_ref=f"source:{chunk.source_id}:{chunk.chunk_id}",
                score=round(max(0.0, score), 6),
            )
            for score, chunk in selected
        ]
        return ProjectRagResult(
            query=request.query,
            k=request.k,
            retrieval_strategy=RETRIEVAL_STRATEGY,
            results=results,
            evidence_refs=[item.evidence_ref for item in results],
            grounding_summary=(
                "Retrieved persisted chunks from the allowlisted Spring Boot/PostgreSQL/Docker "
                "support corpus using real embeddings and native PostgreSQL pgvector cosine "
                "search. Source ids map to the final-project source manifest."
            ),
        )


def build_pgvector_support_rag_service_from_env() -> PgvectorSupportRagService:
    database_url = (
        os.getenv("EACHAT_SUPPORT_RAG_DATABASE_URL", "").strip()
        or os.getenv("EACHAT_POSTGRES_URL", "").strip()
    )
    embedding_key = (
        os.getenv("EACHAT_SUPPORT_EMBEDDING_API_KEY", "").strip()
        or os.getenv("OPENAI_API_KEY", "").strip()
    )
    embedding_model = (
        os.getenv("EACHAT_SUPPORT_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL).strip()
        or DEFAULT_EMBEDDING_MODEL
    )
    raw_dimensions = os.getenv(
        "EACHAT_SUPPORT_EMBEDDING_DIMENSIONS", str(DEFAULT_EMBEDDING_DIMENSIONS)
    ).strip()
    try:
        embedding_dimensions = int(raw_dimensions)
    except ValueError as exc:
        raise SupportRagUnavailableError(
            "EACHAT_SUPPORT_EMBEDDING_DIMENSIONS must be a positive integer"
        ) from exc
    if embedding_dimensions <= 0:
        raise SupportRagUnavailableError(
            "EACHAT_SUPPORT_EMBEDDING_DIMENSIONS must be a positive integer"
        )
    return PgvectorSupportRagService(
        store=PgvectorSupportRagStore(
            database_url,
            embedding_dimensions=embedding_dimensions,
        ),
        embeddings=OpenAIEmbeddingProvider(api_key=embedding_key, model=embedding_model),
    )


@lru_cache(maxsize=1)
def get_pgvector_support_rag_service() -> PgvectorSupportRagService:
    return build_pgvector_support_rag_service_from_env()


def _vector_literal(values: list[float] | tuple[float, ...]) -> str:
    return "[" + ",".join(format(float(value), ".12g") for value in values) + "]"


def _row_to_chunk(row: dict[str, object]) -> SupportChunk:
    return SupportChunk(
        chunk_id=str(row["chunk_id"]),
        source_id=str(row["source_id"]),
        source_family=str(row["source_family"]),
        product=str(row["product"]),
        product_version=str(row["product_version"]),
        title=str(row["title"]),
        canonical_url=str(row["canonical_url"]),
        support_categories=tuple(json.loads(str(row["support_categories"]))),
        section=str(row["section"]),
        content=str(row["content"]),
        content_hash=str(row["content_hash"]),
        ingestion_version=str(row["ingestion_version"]),
        retrieved_at=row["retrieved_at"],  # type: ignore[arg-type]
        embedding_model=str(row["embedding_model"]),
        embedding=tuple(float(value) for value in json.loads(str(row["embedding"]))),
    )


__all__ = [
    "DEFAULT_EMBEDDING_DIMENSIONS",
    "PgvectorSupportRagService",
    "PgvectorSupportRagStore",
    "RETRIEVAL_STRATEGY",
    "build_pgvector_support_rag_service_from_env",
    "get_pgvector_support_rag_service",
]
