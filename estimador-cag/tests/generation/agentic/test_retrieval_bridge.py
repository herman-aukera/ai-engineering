import asyncio

import pytest

from app.embedding_pipeline.search_service import SearchQueryResult, SearchResultItem
from app.generation.agentic.agent_schemas import SearchBudgetsInput
from app.generation.agentic.retrieval_bridge import search_budgets_with_service


class FakeSemanticSearchService:
    def __init__(self):
        self.commands = []

    async def search(self, command):
        self.commands.append(command)
        return SearchQueryResult(
            query=command.query,
            k=command.k,
            filters_applied=command.metadata_filters.as_response_dict(),
            results=[
                SearchResultItem(
                    chunk_id=101,
                    document_id=7,
                    chunk_type="budget_component",
                    content=(
                        "JWT authentication for financial SaaS usually includes "
                        "login, roles, token expiry, and audit-sensitive access checks."
                    ),
                    distance=0.12,
                    metadata={
                        "budget_id": "budget-finance-saas",
                        "component_id": "auth-jwt",
                        "title": "JWT authentication",
                    },
                ),
                SearchResultItem(
                    chunk_id=102,
                    document_id=7,
                    chunk_type="budget_component",
                    content=(
                        "Audit logging covers sensitive actions, exports, "
                        "failed validations, and admin review history."
                    ),
                    distance=0.2,
                    metadata={
                        "budget_id": "budget-finance-saas",
                        "component_id": "audit-log",
                    },
                ),
            ],
        )


def test_search_budgets_with_service_maps_retrieval_results_to_budget_hits():
    service = FakeSemanticSearchService()

    result = asyncio.run(
        search_budgets_with_service(
            SearchBudgetsInput(
                query="JWT authentication and audit logging",
                filters={
                    "client_sector": "finance",
                    "main_technology": "python",
                    "ignored": "not-forwarded",
                },
            ),
            service=service,
            k=2,
        )
    )

    assert result.query == "JWT authentication and audit logging"
    assert [hit.budget_id for hit in result.hits] == [
        "budget-finance-saas",
        "budget-finance-saas",
    ]
    assert result.hits[0].component_id == "auth-jwt"
    assert result.hits[0].title == "JWT authentication"
    assert result.hits[0].score == pytest.approx(0.88)
    assert "financial SaaS" in result.hits[0].snippet

    command = service.commands[0]
    assert command.query == "JWT authentication and audit logging"
    assert command.k == 2
    assert command.search_mode == "hybrid"
    assert command.metadata_filters.client_sector == "finance"
    assert command.metadata_filters.main_technology == "python"
    assert not hasattr(command.metadata_filters, "ignored")


def test_search_budgets_with_service_falls_back_to_chunk_title_when_metadata_title_missing():
    service = FakeSemanticSearchService()

    result = asyncio.run(
        search_budgets_with_service(
            SearchBudgetsInput(query="audit logging"),
            service=service,
            k=2,
        )
    )

    assert result.hits[1].title == "budget_component #102"
    assert result.hits[1].score == pytest.approx(0.8)
