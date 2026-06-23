"""
LAYER: embedding pipeline reranking
RESPONSIBILITY: Provide lightweight deterministic reranking for retrieved chunks.
WHY IT EXISTS: Session 10 needs C/D reranker measurement without forcing heavy
               local model downloads or live provider dependencies in CI.
"""

from __future__ import annotations

import re

from app.embedding_pipeline.search_service import SearchResultItem

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


class KeywordOverlapReranker:
    """Deterministic query-token overlap reranker.

    This is not a cross encoder. It is a CI-safe fallback that makes the
    reranker path executable and measurable. A heavier model-backed reranker can
    later implement the same service protocol.
    """

    def rerank(
        self,
        *,
        query: str,
        items: list[SearchResultItem],
        top_n: int,
    ) -> list[SearchResultItem]:
        """Return candidates ordered by normalized query token overlap."""

        if top_n <= 0:
            raise ValueError("top_n must be positive")

        query_terms = _tokenize(query)
        if not query_terms:
            return items[:top_n]

        scored = sorted(
            enumerate(items),
            key=lambda indexed_item: (
                -_overlap_score(query_terms, indexed_item[1].content),
                indexed_item[0],
            ),
        )
        return [item for _, item in scored[:top_n]]


def _tokenize(text: str) -> set[str]:
    return {match.group(0).lower() for match in _TOKEN_RE.finditer(text)}


def _overlap_score(query_terms: set[str], content: str) -> float:
    content_terms = _tokenize(content)
    if not content_terms:
        return 0.0
    return len(query_terms & content_terms) / len(query_terms)
