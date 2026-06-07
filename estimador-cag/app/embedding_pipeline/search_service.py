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
class SearchMetadataFilters:
    """Exact metadata filters accepted by semantic search."""

    client_sector: str | None = None
    client_country: str | None = None
    main_technology: str | None = None
    complexity: str | None = None
    year: int | None = None
    budget_id: str | None = None
    component_id: str | None = None
    tech_stack: str | None = None
    scope: str | None = None

    def as_response_dict(self) -> dict[str, Any]:
        """Return non-empty filter values as the public response representation."""
        filters: dict[str, Any] = {}
        for key in [
            "client_sector",
            "client_country",
            "main_technology",
            "complexity",
            "year",
            "budget_id",
            "component_id",
            "tech_stack",
            "scope",
        ]:
            value = getattr(self, key)
            if value is None:
                continue
            if isinstance(value, str):
                stripped = value.strip()
                if stripped:
                    filters[key] = stripped
                continue
            filters[key] = value
        return filters

    def as_repository_filter(self) -> dict[str, Any]:
        """Return JSONB containment filters for repository search."""
        filters = self.as_response_dict()
        if "tech_stack" in filters:
            filters["tech_stack"] = [filters["tech_stack"]]
        return filters


@dataclass(frozen=True)
class SearchQueryCommand:
    """Input command for semantic chunk search."""

    query: str
    k: int = 5
    metadata_filters: SearchMetadataFilters = field(default_factory=SearchMetadataFilters)


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
    filters_applied: dict[str, Any] = field(default_factory=dict)


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
            metadata_filters=command.metadata_filters.as_repository_filter(),
        )

        return SearchQueryResult(
            query=query,
            k=command.k,
            results=[_to_search_result_item(row) for row in rows],
            filters_applied=command.metadata_filters.as_response_dict(),
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
