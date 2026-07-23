"""
Session 12 retrieval bridge for agentic budget search.

This module adapts the existing Session 08-10 semantic search service into the
Session 12 search_budgets tool contract without making deterministic CI depend
on a live database or embedding provider.
"""

from __future__ import annotations

from typing import Any, Protocol

from app.embedding_pipeline.search_service import (
    SearchMetadataFilters,
    SearchQueryCommand,
    SearchQueryResult,
    SearchResultItem,
)
from app.generation.agentic.agent_schemas import (
    BudgetSearchHit,
    SearchBudgetsInput,
    SearchBudgetsOutput,
)


class SemanticSearchLike(Protocol):
    """Minimal async service protocol required by the agent retrieval bridge."""

    async def search(self, command: SearchQueryCommand) -> SearchQueryResult:
        """Return semantic search results for a command."""


_ALLOWED_FILTER_KEYS = {
    "client_sector",
    "client_country",
    "main_technology",
    "complexity",
    "year",
    "budget_id",
    "component_id",
    "tech_stack",
    "scope",
}


def _metadata_filters_from_budget_input(
    payload: SearchBudgetsInput,
) -> SearchMetadataFilters:
    """Translate agent search filters into Session 08-10 metadata filters."""

    raw_filters = payload.filters or {}
    safe_filters: dict[str, Any] = {
        key: value
        for key, value in raw_filters.items()
        if key in _ALLOWED_FILTER_KEYS and value is not None
    }
    return SearchMetadataFilters(**safe_filters)


def _score_from_distance(distance: float) -> float:
    """Convert cosine distance-like values into a simple relevance score."""

    return round(max(0.0, 1.0 - float(distance)), 3)


def _snippet(content: str, *, limit: int = 220) -> str:
    """Return a compact one-line snippet for an agent observation."""

    compact = " ".join(content.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _budget_hit_from_search_result(item: SearchResultItem) -> BudgetSearchHit:
    """Map one semantic search result into the Session 12 budget hit contract."""

    metadata = item.metadata or {}
    budget_id = str(metadata.get("budget_id") or item.document_id)
    component_id = metadata.get("component_id")
    title = str(metadata.get("title") or f"{item.chunk_type} #{item.chunk_id}")

    return BudgetSearchHit(
        budget_id=budget_id,
        component_id=str(component_id) if component_id is not None else None,
        title=title,
        snippet=_snippet(item.content),
        score=_score_from_distance(item.distance),
    )


async def search_budgets_with_service(
    payload: SearchBudgetsInput,
    *,
    service: SemanticSearchLike,
    k: int = 5,
    search_mode: str = "hybrid",
    recall_k: int = 50,
) -> SearchBudgetsOutput:
    """
    Search budget-like chunks using an injected semantic search service.

    The injected service makes deterministic tests possible while keeping the
    production boundary compatible with the existing SemanticSearchService.
    """

    command = SearchQueryCommand(
        query=payload.query,
        k=k,
        metadata_filters=_metadata_filters_from_budget_input(payload),
        search_mode=search_mode,
        recall_k=recall_k,
    )
    result = await service.search(command)

    return SearchBudgetsOutput(
        query=result.query,
        hits=[_budget_hit_from_search_result(item) for item in result.results],
    )
