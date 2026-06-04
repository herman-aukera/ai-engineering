"""
LAYER: embedding_pipeline router
RESPONSIBILITY: Expose structural chunking plus embedding through FastAPI.
WHY IT EXISTS: Session 07 needs a minimal HTTP surface that vectorizes budget chunks
               in memory before retrieval, pgvector, or RAG are introduced.
"""

import structlog
from fastapi import APIRouter, HTTPException

from app.embedding_pipeline.chunker import JSONStructuralChunker
from app.embedding_pipeline.embedder import (
    EMBEDDING_MODEL,
    OpenAIEmbedder,
    estimate_embedding_cost_usd,
)
from app.embedding_pipeline.schemas import IngestRequest, IngestResponse, IngestStats

router = APIRouter()
logger = structlog.get_logger(__name__)


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
