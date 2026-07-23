"""Concrete Session 9-12 adapters for the Session 13 graph ports."""

from __future__ import annotations

import asyncio
import json
from collections.abc import (
    AsyncIterator,
    Callable,
    Mapping,
    Sequence,
)
from contextlib import (
    AbstractAsyncContextManager,
    asynccontextmanager,
)
from dataclasses import dataclass
from math import isfinite
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.config import TierName, settings
from app.embedding_pipeline.embedder import OpenAIEmbedder
from app.embedding_pipeline.search_service import (
    SearchQueryCommand,
    SemanticSearchService,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.state import (
    BudgetMatch,
    ComponentItem,
    RequirementItem,
)
from app.persistence.database import AsyncSessionLocal
from app.persistence.repository import DocumentRepository
from app.services.litellm_provider import LiteLLMProvider


class StructuredCompletionProvider(Protocol):
    """Structured completion method inherited from the provider layer."""

    def complete_structured_messages(
        self,
        *,
        messages: list[dict[str, str]],
        tier: TierName,
        response_model: type[BaseModel],
        max_tokens: int,
    ) -> dict[str, object]:
        """Return one Pydantic-validated structured completion."""


class BudgetSearchItem(Protocol):
    """Minimal existing retrieval result required by the adapter."""

    chunk_id: int
    document_id: int
    distance: float
    metadata: dict[str, object]


class BudgetSearchResult(Protocol):
    results: list[BudgetSearchItem]


class BudgetSearchService(Protocol):
    async def search(
        self,
        command: SearchQueryCommand,
    ) -> BudgetSearchResult:
        """Execute the inherited semantic or hybrid retrieval."""


SearchServiceContextFactory = Callable[
    [],
    AbstractAsyncContextManager[BudgetSearchService],
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _RequirementCandidate(_StrictModel):
    text: str = Field(min_length=1)


class _RequirementExtraction(_StrictModel):
    requirements: list[_RequirementCandidate] = Field(
        min_length=1
    )


class _ComponentCandidate(_StrictModel):
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    requirement_ids: list[str] = Field(min_length=1)


class _ComponentClassification(_StrictModel):
    components: list[_ComponentCandidate] = Field(
        min_length=1
    )


def _nonblank_string(
    value: object,
    *,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{field_name} must not be blank")

    return normalized


def _optional_positive_float(
    value: object,
    *,
    field_name: str,
) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(
        value,
        (int, float),
    ):
        raise ValueError(f"{field_name} must be numeric")

    normalized = float(value)

    if not isfinite(normalized) or normalized <= 0:
        raise ValueError(
            f"{field_name} must be finite and positive"
        )

    return normalized


def _structured_result(
    completion: object,
    *,
    response_model: type[BaseModel],
) -> BaseModel:
    if not isinstance(completion, Mapping):
        raise RuntimeError(
            "structured provider response must be a mapping"
        )

    raw_result = completion.get("result")

    if isinstance(raw_result, response_model):
        return raw_result

    try:
        return response_model.model_validate(raw_result)
    except ValidationError as exc:
        raise RuntimeError(
            "structured provider result failed validation"
        ) from exc


@dataclass(frozen=True)
class LiteLLMRequirementExtractor:
    """Extract requirements through the inherited structured provider."""

    provider: StructuredCompletionProvider
    tier: TierName = "flash"

    async def extract_requirements(
        self,
        *,
        transcript: str,
    ) -> list[RequirementItem]:
        messages = [
            {
                "role": "system",
                "content": (
                    "Extract atomic software requirements from the "
                    "transcript. Preserve scope and observable behavior. "
                    "Do not classify implementation components. "
                    "Do not estimate hours, cost, duration, or confidence."
                ),
            },
            {
                "role": "user",
                "content": (
                    "<transcript>\n"
                    f"{transcript}"
                    "\n</transcript>"
                ),
            },
        ]

        completion = await asyncio.to_thread(
            self.provider.complete_structured_messages,
            messages=messages,
            tier=self.tier,
            response_model=_RequirementExtraction,
            max_tokens=1200,
        )
        result = _structured_result(
            completion,
            response_model=_RequirementExtraction,
        )
        parsed = _RequirementExtraction.model_validate(result)

        return [
            {
                "requirement_id": f"REQ-{index:03d}",
                "text": _nonblank_string(
                    candidate.text,
                    field_name="requirement text",
                ),
            }
            for index, candidate in enumerate(
                parsed.requirements,
                start=1,
            )
        ]


@dataclass(frozen=True)
class LiteLLMComponentClassifier:
    """Classify requirements without estimating effort."""

    provider: StructuredCompletionProvider
    tier: TierName = "flash"

    async def classify_components(
        self,
        *,
        requirements: Sequence[RequirementItem],
    ) -> list[ComponentItem]:
        requirements_payload = [
            {
                "requirement_id": item["requirement_id"],
                "text": item["text"],
            }
            for item in requirements
        ]
        messages = [
            {
                "role": "system",
                "content": (
                    "Group the supplied requirements into stable "
                    "implementation components. Every component must "
                    "reference only supplied requirement IDs. "
                    "Do not estimate hours, cost, duration, or confidence."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "requirements": requirements_payload,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            },
        ]

        completion = await asyncio.to_thread(
            self.provider.complete_structured_messages,
            messages=messages,
            tier=self.tier,
            response_model=_ComponentClassification,
            max_tokens=1500,
        )
        result = _structured_result(
            completion,
            response_model=_ComponentClassification,
        )
        parsed = _ComponentClassification.model_validate(result)

        return [
            {
                "component_id": f"CMP-{index:03d}",
                "name": _nonblank_string(
                    candidate.name,
                    field_name="component name",
                ),
                "category": _nonblank_string(
                    candidate.category,
                    field_name="component category",
                ),
                "requirement_ids": [
                    _nonblank_string(
                        requirement_id,
                        field_name="requirement_id",
                    )
                    for requirement_id
                    in candidate.requirement_ids
                ],
            }
            for index, candidate in enumerate(
                parsed.components,
                start=1,
            )
        ]


@asynccontextmanager
async def open_semantic_search_service(
) -> AsyncIterator[BudgetSearchService]:
    """Open the inherited pgvector search service for one operation."""

    async with AsyncSessionLocal.begin() as session:
        yield SemanticSearchService(
            embedder=OpenAIEmbedder(),
            repository=DocumentRepository(session),
        )


@dataclass(frozen=True)
class PgVectorBudgetSearcher:
    """Map existing hybrid retrieval results into graph evidence."""

    search_service_context_factory: (
        SearchServiceContextFactory
    ) = open_semantic_search_service

    async def search_budgets(
        self,
        *,
        component: ComponentItem,
        k: int,
    ) -> list[BudgetMatch]:
        query = " ".join(
            (
                component["name"].strip(),
                component["category"].strip(),
            )
        ).strip()

        async with (
            self.search_service_context_factory()
        ) as search_service:
            result = await search_service.search(
                SearchQueryCommand(
                    query=query,
                    k=k,
                    search_mode="hybrid",
                    recall_k=max(50, k),
                )
            )

        matches: list[BudgetMatch] = []

        for item in result.results:
            metadata = item.metadata

            if not isinstance(metadata, Mapping):
                raise ValueError(
                    "retrieval metadata must be a mapping"
                )

            budget_id = _nonblank_string(
                metadata.get("budget_id"),
                field_name="budget_id",
            )

            raw_reference_component_id = metadata.get(
                "component_id"
            )
            reference_component_id = (
                None
                if raw_reference_component_id is None
                else _nonblank_string(
                    raw_reference_component_id,
                    field_name="component_id",
                )
            )

            recorded_hours = _optional_positive_float(
                metadata.get("estimated_hours"),
                field_name="estimated_hours",
            )

            if (
                isinstance(item.distance, bool)
                or not isinstance(item.distance, (int, float))
            ):
                raise ValueError("distance must be numeric")

            distance = float(item.distance)

            if not isfinite(distance) or distance < 0:
                raise ValueError(
                    "distance must be finite and non-negative"
                )

            matches.append(
                {
                    "component_id": component["component_id"],
                    "budget_id": budget_id,
                    "reference_component_id": (
                        reference_component_id
                    ),
                    "source_document_id": str(
                        item.document_id
                    ),
                    "source_chunk_id": str(item.chunk_id),
                    "recorded_hours": recorded_hours,
                    "distance": distance,
                    "score": round(
                        1.0 / (1.0 + distance),
                        6,
                    ),
                    "retrieval_method": "hybrid",
                }
            )

        return matches


def build_graph_node_dependencies(
    *,
    provider: StructuredCompletionProvider | None = None,
    search_service_context_factory: (
        SearchServiceContextFactory | None
    ) = None,
    tier: TierName | None = None,
    search_k: int = 5,
) -> GraphNodeDependencies:
    """Build concrete runtime dependencies at the composition root."""

    resolved_provider = provider or LiteLLMProvider()
    resolved_tier = tier or settings.llm_tier

    return GraphNodeDependencies(
        requirement_extractor=LiteLLMRequirementExtractor(
            provider=resolved_provider,
            tier=resolved_tier,
        ),
        component_classifier=LiteLLMComponentClassifier(
            provider=resolved_provider,
            tier=resolved_tier,
        ),
        budget_searcher=PgVectorBudgetSearcher(
            search_service_context_factory=(
                search_service_context_factory
                or open_semantic_search_service
            )
        ),
        search_k=search_k,
    )
