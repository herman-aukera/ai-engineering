from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import pytest
from pydantic import BaseModel

from app.generation.graph.adapters import (
    LiteLLMComponentClassifier,
    LiteLLMRequirementExtractor,
    LiteLLMSupervisorRouteProposer,
    PgVectorBudgetSearcher,
    build_graph_node_dependencies,
)
from app.generation.graph.state import ComponentItem
from app.schemas.session14_supervision import SupervisorStateDigest


class FakeStructuredProvider:
    def __init__(
        self,
        payloads: list[dict[str, object]] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.payloads = list(payloads or [])
        self.error = error
        self.calls: list[dict[str, object]] = []

    def complete_structured_messages(
        self,
        *,
        messages: list[dict[str, str]],
        tier: str,
        response_model: type[BaseModel],
        max_tokens: int,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "messages": messages,
                "tier": tier,
                "response_model": response_model,
                "max_tokens": max_tokens,
            }
        )

        if self.error is not None:
            raise self.error

        payload = self.payloads.pop(0)
        return {
            "result": response_model.model_validate(payload),
        }


@dataclass(frozen=True)
class FakeSearchItem:
    chunk_id: int
    document_id: int
    chunk_type: str
    content: str
    distance: float
    metadata: dict[str, Any]


@dataclass(frozen=True)
class FakeSearchResult:
    results: list[FakeSearchItem]


class FakeSearchService:
    def __init__(
        self,
        items: list[FakeSearchItem],
    ) -> None:
        self.items = items
        self.commands: list[object] = []

    async def search(self, command: object) -> FakeSearchResult:
        self.commands.append(command)
        return FakeSearchResult(results=self.items)


class FakeSearchContextFactory:
    def __init__(
        self,
        service: FakeSearchService,
    ) -> None:
        self.service = service
        self.enter_count = 0
        self.exit_count = 0

    def __call__(self):
        @asynccontextmanager
        async def context():
            self.enter_count += 1
            try:
                yield self.service
            finally:
                self.exit_count += 1

        return context()


@pytest.mark.asyncio
async def test_supervisor_route_proposer_uses_only_digest_and_candidates() -> None:
    provider = FakeStructuredProvider(
        [
            {
                "next_agent": "budget_searcher",
                "reason": "Requirements exist; retrieve historical evidence.",
            }
        ]
    )
    adapter = LiteLLMSupervisorRouteProposer(
        provider=provider,
        tier="flash",
    )
    digest = SupervisorStateDigest(
        requirements_count=3,
        requirements_extraction_completed=True,
        budget_match_count=0,
        budget_search_completed=False,
        estimate_ready=False,
        validation_ready=False,
        confidence=None,
        review_required=False,
        routing_steps=1,
        status="pending",
    )

    proposal = await adapter.propose_route(
        digest=digest,
        candidates=("budget_searcher",),
    )

    assert proposal.next_agent == "budget_searcher"
    call = provider.calls[0]
    assert call["tier"] == "flash"
    assert call["max_tokens"] == 300
    assert call["response_model"].__name__ == (
        "SupervisorRouteProposal"
    )
    messages = call["messages"]
    assert isinstance(messages, list)
    assert "budget_searcher" in messages[1]["content"]
    assert "requirements_count" in messages[1]["content"]
    assert "transcript" not in messages[1]["content"]


@pytest.mark.asyncio
async def test_requirement_extractor_assigns_stable_ids() -> None:
    provider = FakeStructuredProvider(
        [
            {
                "requirements": [
                    {
                        "text": "Users authenticate with JWT.",
                    },
                    {
                        "text": (
                            "Sensitive actions are written "
                            "to an audit log."
                        ),
                    },
                ]
            }
        ]
    )
    adapter = LiteLLMRequirementExtractor(
        provider=provider,
        tier="flash",
    )

    requirements = await adapter.extract_requirements(
        transcript=(
            "The client requires JWT authentication and "
            "audit logging for sensitive actions."
        )
    )

    assert requirements == [
        {
            "requirement_id": "REQ-001",
            "text": "Users authenticate with JWT.",
        },
        {
            "requirement_id": "REQ-002",
            "text": (
                "Sensitive actions are written "
                "to an audit log."
            ),
        },
    ]

    call = provider.calls[0]
    assert call["tier"] == "flash"
    assert call["max_tokens"] == 1200
    assert len(call["messages"]) == 2
    assert "Do not estimate hours" in call["messages"][0]["content"]


@pytest.mark.asyncio
async def test_component_classifier_assigns_stable_ids() -> None:
    provider = FakeStructuredProvider(
        [
            {
                "components": [
                    {
                        "name": "JWT authentication",
                        "category": "backend",
                        "requirement_ids": ["REQ-001"],
                    },
                    {
                        "name": "Audit logging",
                        "category": "observability",
                        "requirement_ids": ["REQ-002"],
                    },
                ]
            }
        ]
    )
    adapter = LiteLLMComponentClassifier(
        provider=provider,
        tier="pro",
    )

    components = await adapter.classify_components(
        requirements=[
            {
                "requirement_id": "REQ-001",
                "text": "Users authenticate with JWT.",
            },
            {
                "requirement_id": "REQ-002",
                "text": "Sensitive actions are audited.",
            },
        ]
    )

    assert components == [
        {
            "component_id": "CMP-001",
            "name": "JWT authentication",
            "category": "backend",
            "requirement_ids": ["REQ-001"],
        },
        {
            "component_id": "CMP-002",
            "name": "Audit logging",
            "category": "observability",
            "requirement_ids": ["REQ-002"],
        },
    ]

    call = provider.calls[0]
    assert call["tier"] == "pro"
    assert call["max_tokens"] == 1500
    assert "REQ-001" in call["messages"][1]["content"]
    assert "Do not estimate hours" in call["messages"][0]["content"]


@pytest.mark.asyncio
async def test_model_adapter_propagates_operational_failure() -> None:
    adapter = LiteLLMRequirementExtractor(
        provider=FakeStructuredProvider(
            error=RuntimeError("provider unavailable")
        ),
        tier="flash",
    )

    with pytest.raises(
        RuntimeError,
        match="provider unavailable",
    ):
        await adapter.extract_requirements(
            transcript="A valid software requirement transcript."
        )


@pytest.mark.asyncio
async def test_budget_searcher_maps_existing_metadata() -> None:
    service = FakeSearchService(
        [
            FakeSearchItem(
                chunk_id=101,
                document_id=10,
                chunk_type="budget_component",
                content="JWT authentication component.",
                distance=0.25,
                metadata={
                    "budget_id": "BUD-101",
                    "component_id": "AUTH-01",
                    "estimated_hours": 40,
                },
            )
        ]
    )
    context_factory = FakeSearchContextFactory(service)
    adapter = PgVectorBudgetSearcher(
        search_service_context_factory=context_factory
    )

    component: ComponentItem = {
        "component_id": "CMP-001",
        "name": "JWT authentication",
        "category": "backend",
        "requirement_ids": ["REQ-001"],
    }

    matches = await adapter.search_budgets(
        component=component,
        k=5,
    )

    assert matches == [
        {
            "component_id": "CMP-001",
            "budget_id": "BUD-101",
            "reference_component_id": "AUTH-01",
            "source_document_id": "10",
            "source_chunk_id": "101",
            "recorded_hours": 40.0,
            "distance": 0.25,
            "score": 0.8,
            "retrieval_method": "hybrid",
        }
    ]

    command = service.commands[0]
    assert command.query == "JWT authentication backend"
    assert command.k == 5
    assert command.search_mode == "hybrid"
    assert command.recall_k == 50
    assert context_factory.enter_count == 1
    assert context_factory.exit_count == 1


@pytest.mark.asyncio
async def test_budget_searcher_preserves_missing_hours_as_none() -> None:
    service = FakeSearchService(
        [
            FakeSearchItem(
                chunk_id=101,
                document_id=10,
                chunk_type="budget_component",
                content="JWT authentication component.",
                distance=0.1,
                metadata={
                    "budget_id": "BUD-101",
                    "component_id": "AUTH-01",
                },
            )
        ]
    )
    adapter = PgVectorBudgetSearcher(
        search_service_context_factory=(
            FakeSearchContextFactory(service)
        )
    )

    matches = await adapter.search_budgets(
        component={
            "component_id": "CMP-001",
            "name": "JWT authentication",
            "category": "backend",
            "requirement_ids": ["REQ-001"],
        },
        k=3,
    )

    assert matches[0]["recorded_hours"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("metadata", "distance"),
    [
        (
            {
                "component_id": "AUTH-01",
                "estimated_hours": 40,
            },
            0.1,
        ),
        (
            {
                "budget_id": "BUD-101",
                "component_id": "AUTH-01",
                "estimated_hours": -1,
            },
            0.1,
        ),
        (
            {
                "budget_id": "BUD-101",
                "component_id": "AUTH-01",
                "estimated_hours": 40,
            },
            float("nan"),
        ),
    ],
)
async def test_budget_searcher_rejects_invalid_provenance(
    metadata: dict[str, object],
    distance: float,
) -> None:
    service = FakeSearchService(
        [
            FakeSearchItem(
                chunk_id=101,
                document_id=10,
                chunk_type="budget_component",
                content="Invalid evidence.",
                distance=distance,
                metadata=metadata,
            )
        ]
    )
    adapter = PgVectorBudgetSearcher(
        search_service_context_factory=(
            FakeSearchContextFactory(service)
        )
    )

    with pytest.raises(ValueError):
        await adapter.search_budgets(
            component={
                "component_id": "CMP-001",
                "name": "JWT authentication",
                "category": "backend",
                "requirement_ids": ["REQ-001"],
            },
            k=3,
        )


def test_dependency_factory_wires_concrete_adapters() -> None:
    provider = FakeStructuredProvider([])
    service = FakeSearchService([])
    context_factory = FakeSearchContextFactory(service)

    dependencies = build_graph_node_dependencies(
        provider=provider,
        search_service_context_factory=context_factory,
        tier="flash",
        search_k=7,
    )

    assert isinstance(
        dependencies.requirement_extractor,
        LiteLLMRequirementExtractor,
    )
    assert isinstance(
        dependencies.component_classifier,
        LiteLLMComponentClassifier,
    )
    assert isinstance(
        dependencies.budget_searcher,
        PgVectorBudgetSearcher,
    )
    assert isinstance(
        dependencies.supervisor_route_proposer,
        LiteLLMSupervisorRouteProposer,
    )
    assert dependencies.search_k == 7
