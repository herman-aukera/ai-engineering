"""
LAYER: embedding_pipeline router
RESPONSIBILITY: Expose structural chunking plus embedding through FastAPI.
WHY IT EXISTS: Session 07 needs a minimal HTTP surface that vectorizes budget chunks
               in memory before retrieval, pgvector, or RAG are introduced.
"""

from typing import Annotated

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import Field

from app.embedding_pipeline.chunker import JSONStructuralChunker
from app.embedding_pipeline.comparison import ChunkingQueryComparisonService, QueryRankingComparison
from app.embedding_pipeline.embedder import (
    EMBEDDING_MODEL,
    OpenAIEmbedder,
    estimate_embedding_cost_usd,
)
from app.embedding_pipeline.schemas import IngestRequest, IngestResponse, IngestStats

router = APIRouter()
logger = structlog.get_logger(__name__)


class CompareRequest(IngestRequest):
    """Request body for deterministic chunking comparison."""

    query: str = Field(min_length=1)
    top_k: Annotated[int, Field(ge=1)] = 3


class KeywordTextEmbedder:
    """
    Deterministic fake embedder for chunking comparison demos.

    This intentionally does not call OpenAI. It keeps /embeddings/compare usable
    in tests, /docs, and teaching demos without credentials.
    """

    keywords = [
        "oauth",
        "jwt",
        "authorization",
        "token",
        "authentication",
        "banking",
        "audit",
        "consent",
        "checkout",
        "payment",
        "inventory",
        "stock",
        "document",
        "clinical",
        "upload",
        "telemetry",
        "machine",
        "alert",
        "maintenance",
        "dashboard",
    ]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return simple keyword-count vectors, one vector per text."""
        vectors: list[list[float]] = []

        for text in texts:
            lower_text = text.lower()
            vectors.append(
                [float(lower_text.count(keyword)) for keyword in self.keywords]
            )

        return vectors


@router.post("/ingest", response_model=IngestResponse)
def ingest_embeddings(request: IngestRequest) -> IngestResponse:
    """
    Vectorize normalized historical budgets.

    Pydantic owns 422 validation. Provider or embedding failures are logged with
    internal details but returned to callers as a generic 500 to avoid leaking
    implementation details or credentials.
    """
    chunker = JSONStructuralChunker()
    chunks = chunker.chunk(request.budgets)

    try:
        embedded_chunks = OpenAIEmbedder().embed_many(chunks)
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
def compare_embeddings(request: CompareRequest) -> QueryRankingComparison:
    """
    Compare chunking strategies for one query.

    This endpoint is a deterministic learning lab. It ranks chunks with a small
    keyword-count fake embedder, not with live OpenAI embeddings.
    """
    return ChunkingQueryComparisonService(
        text_embedder=KeywordTextEmbedder()
    ).compare_query(
        budgets=request.budgets,
        query=request.query,
        top_k=request.top_k,
    )
