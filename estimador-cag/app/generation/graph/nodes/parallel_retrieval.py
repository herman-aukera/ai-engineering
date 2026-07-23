"""Bounded Plus-only LangGraph Send fan-out for budget retrieval."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import TypedDict

from langgraph.types import Send

from app.generation.graph.nodes.search_budgets import (
    _evidence_refs,
    _execution_metadata,
    _normalize_matches,
    _validated_components,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.review_state import ReviewedEstimationGraphState
from app.generation.graph.state import BudgetMatch, ComponentItem


class RetrievalWorkerInput(TypedDict):
    component: ComponentItem
    component_index: int
    estimation_id: str
    graph_version: str


async def parallel_retrieval_dispatch(
    state: ReviewedEstimationGraphState,
) -> ReviewedEstimationGraphState:
    """Record a sanitized fan-out event before LangGraph emits Send packets."""

    components = _validated_components(state.get("components"))
    return {
        "trace_events": [
            {
                "event_type": "parallel_retrieval_dispatched",
                "node": "parallel_retrieval_dispatch",
                "summary": f"Dispatched {len(components)} component retrieval workers.",
                "evidence_refs": [component["component_id"] for component in components],
                "state_delta_keys": ["trace_events"],
            }
        ]
    }


def build_parallel_retrieval_nodes(
    dependencies: GraphNodeDependencies,
    *,
    max_concurrency: int,
):
    """Return Send router, bounded worker, and deterministic fan-in node."""

    if max_concurrency <= 0:
        raise ValueError("max_concurrency must be positive")
    semaphore = asyncio.Semaphore(max_concurrency)

    def fan_out(state: ReviewedEstimationGraphState) -> list[Send]:
        components = _validated_components(state.get("components"))
        return [
            Send(
                "parallel_retrieval_worker",
                RetrievalWorkerInput(
                    component=deepcopy(component),
                    component_index=index,
                    estimation_id=str(state.get("estimation_id", "unknown")),
                    graph_version=str(state.get("graph_version", "unknown")),
                ),
            )
            for index, component in enumerate(components)
        ]

    async def worker(state: RetrievalWorkerInput) -> ReviewedEstimationGraphState:
        component = state["component"]
        component_id = component["component_id"]
        status = "success"
        matches: list[BudgetMatch] = []
        error_kind: str | None = None
        try:
            async with semaphore:
                raw_matches = await dependencies.budget_searcher.search_budgets(
                    component=deepcopy(component), k=dependencies.search_k
                )
            if not raw_matches:
                status = "gap"
                error_kind = "missing"
            else:
                matches = _normalize_matches(raw_matches, expected_component_id=component_id)
                if not matches:
                    status = "gap"
                    error_kind = "missing"
        except (AttributeError, KeyError, TypeError, ValueError):
            status = "gap"
            error_kind = "invalid"
        except Exception:
            status = "gap"
            error_kind = "failure"

        envelope: dict[str, object] = {
            "component_id": component_id,
            "component_index": state["component_index"],
            "status": status,
            "error_kind": error_kind,
            "matches": matches,
        }
        return {
            "parallel_retrieval_results": [envelope],
            "trace_events": [
                {
                    "event_type": "parallel_retrieval_worker_completed",
                    "node": "parallel_retrieval_worker",
                    "summary": f"Retrieval worker completed for {component_id} ({status}).",
                    "evidence_refs": [component_id],
                    "state_delta_keys": ["parallel_retrieval_results", "trace_events"],
                }
            ],
        }

    async def fan_in(
        state: ReviewedEstimationGraphState,
    ) -> ReviewedEstimationGraphState:
        components = _validated_components(state.get("components"))
        results = state.get("parallel_retrieval_results", [])
        matches: list[BudgetMatch] = []
        gaps: dict[str, list[str]] = {"missing": [], "invalid": [], "failure": []}
        seen: set[tuple[str, str, str, str, str]] = set()
        for result in sorted(
            results,
            key=lambda item: (
                int(item.get("component_index", 0)),
                str(item.get("component_id", "")),
            ),
        ):
            component_id = str(result.get("component_id", ""))
            error_kind = result.get("error_kind")
            if isinstance(error_kind, str) and error_kind in gaps:
                gaps[error_kind].append(component_id)
            for match in result.get("matches", []):
                key = (
                    match["component_id"],
                    match["budget_id"],
                    str(match["reference_component_id"]),
                    match["source_document_id"],
                    match["source_chunk_id"],
                )
                if key not in seen:
                    seen.add(key)
                    matches.append(match)
        matches.sort(
            key=lambda match: (
                next(
                    i
                    for i, c in enumerate(components)
                    if c["component_id"] == match["component_id"]
                ),
                match["budget_id"],
                str(match["reference_component_id"]),
                match["source_document_id"],
                match["source_chunk_id"],
            )
        )
        errors = []
        if gaps["invalid"]:
            errors.append(
                {
                    "code": "invalid_budget_matches",
                    "message": "Budget search returned invalid provenance for components: "
                    + ", ".join(gaps["invalid"])
                    + ".",
                    "node": "parallel_retrieval_merge",
                    "severity": "error",
                }
            )
        unresolved = [*gaps["missing"], *gaps["failure"]]
        if unresolved:
            errors.append(
                {
                    "code": "missing_budget_matches",
                    "message": "No budget references were found for components: "
                    + ", ".join(unresolved)
                    + ".",
                    "node": "parallel_retrieval_merge",
                    "severity": "warning",
                }
            )
        update: ReviewedEstimationGraphState = {
            "budget_matches": matches,
            "execution_metadata": _execution_metadata(state, budget_match_count=len(matches)),
            "trace_events": [
                {
                    "event_type": "parallel_retrieval_merged",
                    "node": "parallel_retrieval_merge",
                    "summary": f"Merged {len(matches)} canonical budget matches from {len(results)} workers.",
                    "evidence_refs": _evidence_refs(components, matches),
                    "state_delta_keys": ["budget_matches", "execution_metadata", "trace_events"],
                }
            ],
        }
        if errors:
            update["errors"] = errors
            update["review_required"] = True
        return update

    return fan_out, worker, fan_in
