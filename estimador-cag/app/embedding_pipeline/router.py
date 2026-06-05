"""
LAYER: embedding_pipeline router
RESPONSIBILITY: Expose structural chunking plus embedding through FastAPI.
WHY IT EXISTS: Session 07 needs a minimal HTTP surface that vectorizes budget chunks
               in memory before retrieval, pgvector, or RAG are introduced.
"""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field

from app.embedding_pipeline.chunker import JSONStructuralChunker
from app.embedding_pipeline.comparison import ChunkingQueryComparisonService, QueryRankingComparison
from app.embedding_pipeline.embedder import (
    EMBEDDING_MODEL,
    OpenAIEmbedder,
    estimate_embedding_cost_usd,
)
from app.embedding_pipeline.keyword_embedder import KeywordTextEmbedder
from app.embedding_pipeline.schemas import IngestRequest, IngestResponse, IngestStats

router = APIRouter()
logger = structlog.get_logger(__name__)


def get_openai_embedder() -> OpenAIEmbedder:
    """Build the live OpenAI embedder for the ingestion endpoint."""
    return OpenAIEmbedder()


def get_query_comparison_service() -> ChunkingQueryComparisonService:
    """Build the deterministic comparison service for the lab endpoint."""
    return ChunkingQueryComparisonService(text_embedder=KeywordTextEmbedder())


OpenAIEmbedderDependency = Annotated[OpenAIEmbedder, Depends(get_openai_embedder)]
QueryComparisonServiceDependency = Annotated[
    ChunkingQueryComparisonService,
    Depends(get_query_comparison_service),
]


class CompareRequest(IngestRequest):
    """Request body for deterministic chunking comparison."""

    query: str = Field(min_length=1)
    top_k: Annotated[int, Field(ge=1)] = 3


@router.post("/ingest", response_model=IngestResponse)
def ingest_embeddings(
    request: IngestRequest,
    embedder: OpenAIEmbedderDependency,
) -> IngestResponse:
    """
    Vectorize normalized historical budgets.

    Pydantic owns 422 validation. Provider or embedding failures are logged with
    internal details but returned to callers as a generic 500 to avoid leaking
    implementation details or credentials.
    """
    chunker = JSONStructuralChunker()
    chunks = chunker.chunk(request.budgets)

    try:
        embedded_chunks = embedder.embed_many(chunks)
    except Exception:
        logger.exception(
            "embedding_ingest_failed",
            total_budgets=len(request.budgets),
            total_chunks=len(chunks),
            model=EMBEDDING_MODEL,
        )
        raise HTTPException(status_code=500, detail="Embedding ingestion failed") from None

    total_tokens = sum(chunk.token_count for chunk in chunks)

    return IngestResponse(
        chunks=embedded_chunks,
        stats=IngestStats(
            total_budgets=len(request.budgets),
            total_chunks=len(chunks),
            total_tokens=total_tokens,
            estimated_cost_usd=estimate_embedding_cost_usd(total_tokens),
            model=EMBEDDING_MODEL,
        ),
    )


@router.post("/compare", response_model=QueryRankingComparison)
def compare_embeddings(
    request: CompareRequest,
    comparison_service: QueryComparisonServiceDependency,
) -> QueryRankingComparison:
    """
    Compare chunking strategies for one query.

    This endpoint is a deterministic learning lab. It ranks chunks with a small
    keyword-count fake embedder, not with live OpenAI embeddings.
    """
    return comparison_service.compare_query(
        budgets=request.budgets,
        query=request.query,
        top_k=request.top_k,
    )
