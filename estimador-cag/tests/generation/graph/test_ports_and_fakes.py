from __future__ import annotations

import json

import pytest

from app.generation.graph.fakes import (
    FakeBudgetSearcher,
    FakeComponentClassifier,
    FakeRequirementExtractor,
)
from app.generation.graph.ports import (
    BudgetSearcher,
    ComponentClassifier,
    GraphNodeDependencies,
    RequirementExtractor,
)

REQUIREMENTS = [
    {
        "requirement_id": "REQ-001",
        "text": "Users authenticate with JWT.",
    },
    {
        "requirement_id": "REQ-002",
        "text": "Sensitive actions are written to an audit log.",
    },
]

COMPONENTS = [
    {
        "component_id": "CMP-001",
        "name": "JWT authentication",
        "category": "backend",
        "requirement_ids": ["REQ-001"],
    },
    {
        "component_id": "CMP-002",
        "name": "Audit logging",
        "category": "backend",
        "requirement_ids": ["REQ-002"],
    },
]

BUDGET_MATCHES = {
    "CMP-001": [
        {
            "component_id": "CMP-001",
            "budget_id": "BUD-2024-014",
            "reference_component_id": "AUTH-001",
            "source_document_id": "17",
            "source_chunk_id": "201",
            "recorded_hours": 40.0,
            "distance": 0.08,
            "score": 0.92,
            "retrieval_method": "hybrid",
        }
    ]
}


def test_fakes_satisfy_runtime_protocols() -> None:
    requirement_extractor = FakeRequirementExtractor(REQUIREMENTS)
    component_classifier = FakeComponentClassifier(COMPONENTS)
    budget_searcher = FakeBudgetSearcher(BUDGET_MATCHES)

    assert isinstance(requirement_extractor, RequirementExtractor)
    assert isinstance(component_classifier, ComponentClassifier)
    assert isinstance(budget_searcher, BudgetSearcher)


@pytest.mark.parametrize("search_k", [0, -1])
def test_graph_dependencies_reject_non_positive_search_k(search_k: int) -> None:
    with pytest.raises(ValueError, match="search_k must be positive"):
        GraphNodeDependencies(
            requirement_extractor=FakeRequirementExtractor(REQUIREMENTS),
            component_classifier=FakeComponentClassifier(COMPONENTS),
            budget_searcher=FakeBudgetSearcher(BUDGET_MATCHES),
            search_k=search_k,
        )


@pytest.mark.asyncio
async def test_fake_requirement_extractor_records_call_and_returns_copy() -> None:
    fake = FakeRequirementExtractor(REQUIREMENTS)

    first = await fake.extract_requirements(
        transcript="The client needs JWT authentication and audit logging."
    )
    first[0]["text"] = "mutated by test"

    second = await fake.extract_requirements(
        transcript="The client needs JWT authentication and audit logging."
    )

    assert fake.calls == [
        "The client needs JWT authentication and audit logging.",
        "The client needs JWT authentication and audit logging.",
    ]
    assert second == REQUIREMENTS
    assert second is not REQUIREMENTS
    assert second[0] is not REQUIREMENTS[0]


@pytest.mark.asyncio
async def test_fake_component_classifier_records_requirements_and_returns_copy() -> None:
    fake = FakeComponentClassifier(COMPONENTS)

    first = await fake.classify_components(requirements=REQUIREMENTS)
    first[0]["name"] = "mutated by test"

    second = await fake.classify_components(requirements=REQUIREMENTS)

    assert len(fake.calls) == 2
    assert fake.calls[0] == REQUIREMENTS
    assert fake.calls[0] is not REQUIREMENTS
    assert second == COMPONENTS
    assert second[0] is not COMPONENTS[0]


@pytest.mark.asyncio
async def test_fake_budget_searcher_returns_matches_by_component_id() -> None:
    fake = FakeBudgetSearcher(BUDGET_MATCHES)

    first = await fake.search_budgets(component=COMPONENTS[0], k=5)
    first[0]["recorded_hours"] = 999.0

    second = await fake.search_budgets(component=COMPONENTS[0], k=5)

    assert fake.calls == [
        {"component_id": "CMP-001", "k": 5},
        {"component_id": "CMP-001", "k": 5},
    ]
    assert second == BUDGET_MATCHES["CMP-001"]
    assert second[0]["recorded_hours"] == 40.0
    assert second[0] is not BUDGET_MATCHES["CMP-001"][0]


@pytest.mark.asyncio
async def test_fake_budget_searcher_returns_empty_for_unknown_component() -> None:
    fake = FakeBudgetSearcher(BUDGET_MATCHES)

    matches = await fake.search_budgets(component=COMPONENTS[1], k=3)

    assert matches == []
    assert fake.calls == [{"component_id": "CMP-002", "k": 3}]


@pytest.mark.asyncio
async def test_fake_outputs_remain_json_serializable() -> None:
    requirement_extractor = FakeRequirementExtractor(REQUIREMENTS)
    component_classifier = FakeComponentClassifier(COMPONENTS)
    budget_searcher = FakeBudgetSearcher(BUDGET_MATCHES)

    requirements = await requirement_extractor.extract_requirements(
        transcript="Valid transcript for checkpoint-safe fake outputs."
    )
    components = await component_classifier.classify_components(requirements=requirements)
    matches = await budget_searcher.search_budgets(component=components[0], k=5)

    serialized = json.dumps(
        {
            "requirements": requirements,
            "components": components,
            "matches": matches,
        },
        sort_keys=True,
    )

    assert '"recorded_hours": 40.0' in serialized
