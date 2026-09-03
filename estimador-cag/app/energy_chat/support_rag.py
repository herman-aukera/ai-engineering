"""Real, product-local RAG for the EACHAT final-project L2 support domain.

The final-project path intentionally keeps acquisition, embedding and persistence
behind injectable contracts so deterministic CI never needs network or paid model calls.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.energy_chat.contracts import ProjectRagChunk, ProjectRagRequest, ProjectRagResult

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_MAX_SOURCE_BYTES = 2_000_000
DEFAULT_FETCH_TIMEOUT_SECONDS = 20
DEFAULT_CHUNK_WORDS = 320
DEFAULT_CHUNK_OVERLAP_WORDS = 40


class SupportRagUnavailableError(RuntimeError):
    """Raised when the final-project RAG cannot safely serve evidence."""


@dataclass(frozen=True)
class SupportSource:
    source_id: str
    source_family: str
    product: str
    product_version: str
    title: str
    canonical_url: str
    support_categories: tuple[str, ...]


@dataclass(frozen=True)
class SupportChunk:
    chunk_id: str
    source_id: str
    source_family: str
    product: str
    product_version: str
    title: str
    canonical_url: str
    support_categories: tuple[str, ...]
    section: str
    content: str
    content_hash: str
    ingestion_version: str
    retrieved_at: datetime
    embedding_model: str
    embedding: tuple[float, ...]


class EmbeddingProvider(Protocol):
    model: str

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


class SupportRagStore(Protocol):
    def setup(self) -> None: ...

    def replace_source_chunks(self, source_id: str, chunks: list[SupportChunk]) -> None: ...

    def list_active_chunks(self) -> list[SupportChunk]: ...

    def count_active_chunks(self) -> int: ...


class OpenAIEmbeddingProvider:
    """Small production embedding adapter using the already-locked OpenAI SDK."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_EMBEDDING_MODEL,
        client: object | None = None,
        batch_size: int = 100,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("Embedding batch_size must be positive")
        self.model = model
        self.batch_size = batch_size
        if client is None:
            key = (api_key or "").strip()
            if not key:
                raise SupportRagUnavailableError(
                    "EACHAT support RAG requires EACHAT_SUPPORT_EMBEDDING_API_KEY "
                    "or OPENAI_API_KEY for query/document embeddings."
                )
            from openai import OpenAI

            client = OpenAI(api_key=key)
        self._client = client

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            response = self._client.embeddings.create(model=self.model, input=batch)
            batch_vectors = [list(item.embedding) for item in response.data]
            if len(batch_vectors) != len(batch):
                raise RuntimeError("Embedding provider returned a mismatched vector count")
            if any(not vector for vector in batch_vectors):
                raise RuntimeError("Embedding provider returned an empty vector")
            vectors.extend(batch_vectors)
        return vectors


class InMemorySupportRagStore:
    """Deterministic test store; production uses PostgreSQL."""

    def __init__(self) -> None:
        self._chunks: dict[str, SupportChunk] = {}

    def setup(self) -> None:
        return None

    def replace_source_chunks(self, source_id: str, chunks: list[SupportChunk]) -> None:
        self._chunks = {
            chunk_id: chunk
            for chunk_id, chunk in self._chunks.items()
            if chunk.source_id != source_id
        }
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk

    def list_active_chunks(self) -> list[SupportChunk]:
        return [self._chunks[key] for key in sorted(self._chunks)]

    def count_active_chunks(self) -> int:
        return len(self._chunks)


class PostgresSupportRagStore:
    """Persistent support corpus using PostgreSQL plus exact cosine retrieval."""

    def __init__(self, connection_string: str) -> None:
        if not connection_string.strip():
            raise SupportRagUnavailableError(
                "EACHAT support RAG requires EACHAT_SUPPORT_RAG_DATABASE_URL "
                "or EACHAT_POSTGRES_URL."
            )
        self._connection_string = connection_string

    def _connect(self):
        from psycopg import connect
        from psycopg.rows import dict_row

        return connect(self._connection_string, row_factory=dict_row)

    def setup(self) -> None:
        statements = (
            """
            CREATE TABLE IF NOT EXISTS eachat_support_rag_chunks (
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
                embedding JSONB NOT NULL,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_eachat_support_rag_active_family
            ON eachat_support_rag_chunks (active, source_family)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_eachat_support_rag_source
            ON eachat_support_rag_chunks (source_id)
            """,
        )
        with self._connect() as connection:
            for statement in statements:
                connection.execute(statement)

    def replace_source_chunks(self, source_id: str, chunks: list[SupportChunk]) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE eachat_support_rag_chunks SET active = FALSE, updated_at = NOW() "
                "WHERE source_id = %s",
                (source_id,),
            )
            for chunk in chunks:
                connection.execute(
                    """
                    INSERT INTO eachat_support_rag_chunks (
                        chunk_id, source_id, source_family, product, product_version,
                        title, canonical_url, support_categories, section, content,
                        content_hash, ingestion_version, retrieved_at, embedding_model,
                        embedding, active, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s,
                        %s, %s, %s, %s, %s::jsonb, TRUE, NOW()
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
                        json.dumps(list(chunk.embedding)),
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
                FROM eachat_support_rag_chunks
                WHERE active = TRUE
                ORDER BY chunk_id
                """
            ).fetchall()
        return [_row_to_chunk(row) for row in rows]

    def count_active_chunks(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM eachat_support_rag_chunks WHERE active = TRUE"
            ).fetchone()
        return int(row["count"])


class _SupportHtmlParser(HTMLParser):
    _skip_tags = {"script", "style", "nav", "header", "footer", "noscript", "svg"}
    _heading_tags = {"h1", "h2", "h3"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._heading_depth = 0
        self._heading_parts: list[str] = []
        self._body_parts: list[str] = []
        self._current_heading = "Document"
        self.sections: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        normalized = tag.casefold()
        if normalized in self._skip_tags:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if normalized in self._heading_tags:
            self._flush_section()
            self._heading_depth += 1
            self._heading_parts = []
        elif normalized in {"p", "li", "pre", "br", "tr"}:
            self._body_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.casefold()
        if normalized in self._skip_tags:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if normalized in self._heading_tags and self._heading_depth:
            heading = _normalize_space(" ".join(self._heading_parts))
            if heading:
                self._current_heading = heading
            self._heading_depth = 0
            self._heading_parts = []
        elif normalized in {"p", "li", "pre", "tr"}:
            self._body_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._heading_depth:
            self._heading_parts.append(data)
        else:
            self._body_parts.append(data)

    def finish(self) -> list[tuple[str, str]]:
        self._flush_section()
        return self.sections

    def _flush_section(self) -> None:
        body = _normalize_block(" ".join(self._body_parts))
        if body:
            self.sections.append((self._current_heading, body))
        self._body_parts = []


def load_source_manifest(path: str | Path) -> tuple[tuple[str, ...], str, list[SupportSource]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    allowed_hosts = tuple(str(host).casefold() for host in payload.get("allowed_hosts", []))
    ingestion_version = str(payload.get("ingestion_version", "")).strip()
    if not allowed_hosts or not ingestion_version:
        raise ValueError("Support source manifest requires allowed_hosts and ingestion_version")

    sources: list[SupportSource] = []
    seen: set[str] = set()
    for raw in payload.get("sources", []):
        source = SupportSource(
            source_id=str(raw["source_id"]).strip(),
            source_family=str(raw["source_family"]).strip(),
            product=str(raw["product"]).strip(),
            product_version=str(raw.get("product_version", "unknown")).strip() or "unknown",
            title=str(raw["title"]).strip(),
            canonical_url=str(raw["canonical_url"]).strip(),
            support_categories=tuple(str(item).strip() for item in raw.get("support_categories", [])),
        )
        if not source.source_id or source.source_id in seen:
            raise ValueError("Support source ids must be non-empty and unique")
        _validate_official_url(source.canonical_url, allowed_hosts)
        seen.add(source.source_id)
        sources.append(source)
    if not sources:
        raise ValueError("Support source manifest contains no sources")
    return allowed_hosts, ingestion_version, sources


def fetch_official_html(
    url: str,
    allowed_hosts: tuple[str, ...],
    *,
    timeout_seconds: int = DEFAULT_FETCH_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
) -> str:
    _validate_official_url(url, allowed_hosts)
    request = Request(
        url,
        headers={
            "User-Agent": "EACHAT-finalproject-ingester/1.0 (+educational RAG; bounded fetch)"
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - URL allowlist enforced
        final_url = response.geturl()
        _validate_official_url(final_url, allowed_hosts)
        content_type = response.headers.get("Content-Type", "").casefold()
        if "text/html" not in content_type:
            raise ValueError(f"Unsupported source content type for {url}: {content_type}")
        payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ValueError(f"Source exceeds bounded fetch size: {url}")
    return payload.decode("utf-8", errors="replace")


def extract_sections(html: str) -> list[tuple[str, str]]:
    parser = _SupportHtmlParser()
    parser.feed(html)
    sections = parser.finish()
    return [(heading, body) for heading, body in sections if len(body.split()) >= 10]


def chunk_sections(
    source: SupportSource,
    sections: list[tuple[str, str]],
    *,
    ingestion_version: str,
    retrieved_at: datetime,
    embedding_model: str,
    embeddings: EmbeddingProvider,
    max_words: int = DEFAULT_CHUNK_WORDS,
    overlap_words: int = DEFAULT_CHUNK_OVERLAP_WORDS,
) -> list[SupportChunk]:
    if max_words <= 0 or overlap_words < 0 or overlap_words >= max_words:
        raise ValueError("Invalid support chunk window")

    drafts: list[tuple[str, str, str, str]] = []
    for section, body in sections:
        words = body.split()
        start = 0
        ordinal = 0
        while start < len(words):
            text = " ".join(words[start : start + max_words]).strip()
            if not text:
                break
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            chunk_seed = f"{source.source_id}|{section}|{ordinal}|{content_hash}"
            chunk_id = hashlib.sha256(chunk_seed.encode("utf-8")).hexdigest()[:24]
            drafts.append((chunk_id, section, text, content_hash))
            if start + max_words >= len(words):
                break
            start += max_words - overlap_words
            ordinal += 1

    vectors = embeddings.embed_texts([draft[2] for draft in drafts])
    if len(vectors) != len(drafts):
        raise RuntimeError("Embedding count does not match generated support chunks")

    return [
        SupportChunk(
            chunk_id=chunk_id,
            source_id=source.source_id,
            source_family=source.source_family,
            product=source.product,
            product_version=source.product_version,
            title=source.title,
            canonical_url=source.canonical_url,
            support_categories=source.support_categories,
            section=section,
            content=text,
            content_hash=content_hash,
            ingestion_version=ingestion_version,
            retrieved_at=retrieved_at,
            embedding_model=embedding_model,
            embedding=tuple(float(value) for value in vector),
        )
        for (chunk_id, section, text, content_hash), vector in zip(drafts, vectors, strict=True)
    ]


class SupportRagService:
    def __init__(self, *, store: SupportRagStore, embeddings: EmbeddingProvider) -> None:
        self.store = store
        self.embeddings = embeddings

    def ingest_manifest(
        self,
        manifest_path: str | Path,
        *,
        fetcher=fetch_official_html,
    ) -> dict[str, object]:
        allowed_hosts, ingestion_version, sources = load_source_manifest(manifest_path)
        self.store.setup()
        source_counts: dict[str, int] = {}
        retrieved_at = datetime.now(timezone.utc)
        for source in sources:
            html = fetcher(source.canonical_url, allowed_hosts)
            sections = extract_sections(html)
            if not sections:
                raise ValueError(f"No usable document sections extracted from {source.source_id}")
            chunks = chunk_sections(
                source,
                sections,
                ingestion_version=ingestion_version,
                retrieved_at=retrieved_at,
                embedding_model=self.embeddings.model,
                embeddings=self.embeddings,
            )
            if not chunks:
                raise ValueError(f"No chunks generated from {source.source_id}")
            self.store.replace_source_chunks(source.source_id, chunks)
            source_counts[source.source_id] = len(chunks)
        return {
            "sources_ingested": len(source_counts),
            "active_chunks": self.store.count_active_chunks(),
            "chunks_by_source": source_counts,
            "embedding_model": self.embeddings.model,
            "ingestion_version": ingestion_version,
        }

    def retrieve(self, request: ProjectRagRequest) -> ProjectRagResult:
        self.store.setup()
        chunks = self.store.list_active_chunks()
        if not chunks:
            raise SupportRagUnavailableError(
                "EACHAT support RAG contains no active chunks. Run the support ingestion command first."
            )
        query_vector = self.embeddings.embed_texts([request.query])[0]
        ranked = sorted(
            ((_cosine_similarity(query_vector, chunk.embedding), chunk) for chunk in chunks),
            key=lambda item: (-item[0], item[1].chunk_id),
        )
        selected = ranked[: request.k]
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
            retrieval_strategy="openai_embedding_postgres_exact_cosine_support_rag",
            results=results,
            evidence_refs=[item.evidence_ref for item in results],
            grounding_summary=(
                "Retrieved persisted chunks from the allowlisted Spring Boot/PostgreSQL/Docker "
                "support corpus using real embeddings and exact cosine similarity. Source ids "
                "map to canonical URLs in docs/final_project/support_source_manifest.json."
            ),
        )


def build_support_rag_service_from_env() -> SupportRagService:
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
    return SupportRagService(
        store=PostgresSupportRagStore(database_url),
        embeddings=OpenAIEmbeddingProvider(api_key=embedding_key, model=embedding_model),
    )


@lru_cache(maxsize=1)
def get_support_rag_service() -> SupportRagService:
    return build_support_rag_service_from_env()


def _validate_official_url(url: str, allowed_hosts: tuple[str, ...]) -> None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").casefold()
    if parsed.scheme != "https" or host not in allowed_hosts:
        raise ValueError(f"Source URL is outside the official HTTPS allowlist: {url}")


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_block(value: str) -> str:
    lines = [_normalize_space(line) for line in value.splitlines()]
    return "\n".join(line for line in lines if line)


def _cosine_similarity(left: list[float], right: tuple[float, ...]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("Embedding vectors must be non-empty and have matching dimensions")
    dot = sum(float(a) * float(b) for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(float(value) ** 2 for value in left))
    right_norm = math.sqrt(sum(float(value) ** 2 for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


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
    "InMemorySupportRagStore",
    "OpenAIEmbeddingProvider",
    "PostgresSupportRagStore",
    "SupportChunk",
    "SupportRagService",
    "SupportRagUnavailableError",
    "SupportSource",
    "build_support_rag_service_from_env",
    "chunk_sections",
    "extract_sections",
    "fetch_official_html",
    "get_support_rag_service",
    "load_source_manifest",
]
