"""Read-only dashboard endpoint for graph shadow rollout evidence."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.schemas.graph_rollout import ShadowComparisonList
from app.services.graph_rollout import GLOBAL_GRAPH_SHADOW_STORE

router = APIRouter(prefix="/api/v1", tags=["graph-rollout"])


@router.get(
    "/estimate/graph/shadow/comparisons",
    response_model=ShadowComparisonList,
)
def list_graph_shadow_comparisons(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ShadowComparisonList:
    """Return newest-first sanitized legacy-versus-graph comparisons."""

    comparisons = GLOBAL_GRAPH_SHADOW_STORE.list(limit=limit)
    return ShadowComparisonList(
        count=len(comparisons),
        comparisons=comparisons,
    )
