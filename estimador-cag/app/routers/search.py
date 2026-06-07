"""
LAYER: search router
RESPONSIBILITY: Expose Session 08 semantic chunk search over persisted pgvector data.
WHY IT EXISTS: Search is the public retrieval API built on top of query embeddings,
               PostgreSQL persistence, and cosine-distance retrieval.
"""

from __future__ import annotations

import time
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.embedding_pipeline.embedder import OpenAIEmbedder
from app.embedding_pipeline.search_service import (
    SearchMetadataFilters,
    SearchQueryCommand,
    SemanticSearchService,
)
from app.persistence.database import AsyncSessionLocal
from app.persistence.repository import DocumentRepository

router = APIRouter()
logger = structlog.get_logger(__name__)


class SearchRequest(BaseModel):
    """Request body for semantic chunk search."""

    query: str = Field(min_length=1)
    k: int = Field(default=5, ge=1)
    client_sector: str | None = None
    client_country: str | None = None
    main_technology: str | None = None
    complexity: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)
    budget_id: str | None = None
    component_id: str | None = None
    tech_stack: str | None = None
    scope: str | None = None

    def to_metadata_filters(self) -> SearchMetadataFilters:
        """Convert optional request fields into service metadata filters."""
        return SearchMetadataFilters(
            client_sector=self.client_sector,
            client_country=self.client_country,
            main_technology=self.main_technology,
            complexity=self.complexity,
            year=self.year,
            budget_id=self.budget_id,
            component_id=self.component_id,
            tech_stack=self.tech_stack,
            scope=self.scope,
        )


class SearchResultResponse(BaseModel):
    """One chunk result returned by semantic search."""

    chunk_id: int
    document_id: int
    chunk_type: str
    content: str
    distance: float
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    """Response body for semantic chunk search."""

    query: str
    k: int
    search_time_ms: int = Field(ge=0)
    filters_applied: dict[str, Any] = Field(default_factory=dict)
    results: list[SearchResultResponse]


def get_search_service(session) -> SemanticSearchService:
    """Build the Session 08 semantic search service lazily."""
    return SemanticSearchService(
        embedder=OpenAIEmbedder(),
        repository=DocumentRepository(session),
    )


@router.post("/search", response_model=SearchResponse)
async def search_chunks(request: SearchRequest) -> SearchResponse:
    """Return top-k persisted chunks ordered by cosine distance."""
    started = time.perf_counter()
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="query must not be empty")

    try:
        async with AsyncSessionLocal.begin() as session:
            service = get_search_service(session)
            result = await service.search(
                SearchQueryCommand(
                    query=query,
                    k=request.k,
                    metadata_filters=request.to_metadata_filters(),
                )
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except Exception:
        logger.exception("semantic_search_failed", query=query, k=request.k)
        raise HTTPException(status_code=500, detail="Semantic search failed") from None

    return SearchResponse(
        query=result.query,
        k=result.k,
        search_time_ms=int((time.perf_counter() - started) * 1000),
        filters_applied=result.filters_applied,
        results=[
            SearchResultResponse(
                chunk_id=item.chunk_id,
                document_id=item.document_id,
                chunk_type=item.chunk_type,
                content=item.content,
                distance=item.distance,
                metadata=item.metadata,
            )
            for item in result.results
        ],
    )
