"""
LAYER: persistence repository
RESPONSIBILITY: Persist and retrieve pgvector-backed document/chunk records.
WHY IT EXISTS: Keeps SQLAlchemy details out of FastAPI routers and ingestion
               orchestration while preserving transaction control in services.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import Chunk, Document

EMBEDDING_DIMENSION = 1536


@dataclass(frozen=True)
class ChunkInsert:
    """A chunk row ready to be inserted into pgvector storage."""

    chunk_type: str
    content: str
    embedding: list[float] | None
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        if self.embedding is not None and len(self.embedding) != EMBEDDING_DIMENSION:
            raise ValueError(f"Embedding dimension must be {EMBEDDING_DIMENSION}")


class DocumentRepository:
    """Repository for document and chunk persistence.

    This class deliberately does not commit. Callers own the transaction boundary,
    which allows ingestion to rollback document and chunk writes atomically.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_document_id_by_source_path(self, source_path: str) -> int | None:
        """Return an existing document id for a source path, if present."""
        result = await self.session.execute(
            select(Document.id).where(Document.source_path == source_path)
        )
        return result.scalar_one_or_none()

    async def add_document_with_chunks(
        self,
        *,
        source_path: str,
        document_type: str,
        chunks: list[ChunkInsert],
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Add one document and its chunks to the current session."""
        if not chunks:
            raise ValueError("At least one chunk is required")

        document = Document(
            source_path=source_path,
            document_type=document_type,
            document_metadata=metadata or {},
        )
        self.session.add(document)
        await self.session.flush()

        document_id = int(document.id)
        for chunk in chunks:
            self.session.add(
                Chunk(
                    document_id=document_id,
                    chunk_type=chunk.chunk_type,
                    content=chunk.content,
                    embedding=chunk.embedding,
                    chunk_metadata=chunk.metadata,
                )
            )

        await self.session.flush()
        return document_id
