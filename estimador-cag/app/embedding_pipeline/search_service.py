"""
LAYER: semantic search service
RESPONSIBILITY: Embed a query and retrieve nearest persisted chunks by cosine distance.
WHY IT EXISTS: Session 08 introduces pgvector retrieval before wiring the /search API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.persistence.repository import ChunkSearchResult, DocumentRepository


class QueryEmbedder(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


@dataclass(frozen=True)
class SearchQueryCommand:
    """Input command for semantic chunk search."""

    query: str
    k: int = 5


@dataclass(frozen=True)
class SearchResultItem:
    """One result returned from semantic search."""

    chunk_id: int
    document_id: int
    chunk_type: str
    content: str
    distance: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchQueryResult:
    """Semantic search result envelope."""

    query: str
    k: int
    results: list[SearchResultItem]


class SemanticSearchService:
    """Application service for query embedding plus pgvector retrieval."""

    def __init__(
        self,
        *,
        embedder: QueryEmbedder,
        repository: DocumentRepository,
    ) -> None:
        self.embedder = embedder
        self.repository = repository

    async def search(self, command: SearchQueryCommand) -> SearchQueryResult:
        """Embed the query once and return nearest persisted chunks."""
        query = command.query.strip()
        if not query:
            raise ValueError("query must not be empty")
        if command.k <= 0:
            raise ValueError("k must be positive")

        embeddings = self.embedder.embed_texts([query])
        if len(embeddings) != 1:
            raise ValueError("Query embedding count mismatch")

        rows = await self.repository.search_chunks_by_embedding(
            query_embedding=embeddings[0],
            k=command.k,
        )

        return SearchQueryResult(
            query=query,
            k=command.k,
            results=[_to_search_result_item(row) for row in rows],
        )


def _to_search_result_item(row: ChunkSearchResult) -> SearchResultItem:
    return SearchResultItem(
        chunk_id=row.chunk_id,
        document_id=row.document_id,
        chunk_type=row.chunk_type,
        content=row.content,
        distance=row.distance,
        metadata=row.metadata,
    )
