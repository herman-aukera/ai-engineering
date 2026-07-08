import asyncio

from app.embedding_pipeline.search_service import SearchQueryResult, SearchResultItem
from app.generation.agentic.agent_loop import run_agent_loop_with_retrieval
from app.generation.agentic.agent_schemas import AgentRunRequest


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
                    chunk_id=201,
                    document_id=17,
                    chunk_type="budget_component",
                    content=(
                        "JWT authentication estimate reference: login, role checks, "
                        "token expiry, refresh handling, and secure admin access."
                    ),
                    distance=0.1,
                    metadata={
                        "budget_id": "finance-saas-reference",
                        "component_id": "jwt-auth",
                        "title": "JWT authentication reference",
                    },
                ),
                SearchResultItem(
                    chunk_id=202,
                    document_id=17,
                    chunk_type="budget_component",
                    content=(
                        "Audit logging estimate reference: sensitive actions, "
                        "export logs, failed validation records, and reviewer history."
                    ),
                    distance=0.18,
                    metadata={
                        "budget_id": "finance-saas-reference",
                        "component_id": "audit-logging",
                        "title": "Audit logging reference",
                    },
                ),
            ],
        )


def test_agent_loop_with_retrieval_service_records_non_empty_search_hits():
    request = AgentRunRequest(
        transcript=(
            "Client needs a web SaaS for financial operations with JWT "
            "authentication, audit logging, admin dashboard, and CSV import."
        ),
        provider="fake",
        max_iterations=8,
    )
    service = FakeSemanticSearchService()

    result = asyncio.run(
        run_agent_loop_with_retrieval(
            request,
            search_service=service,
            search_k=2,
        )
    )

    assert result.terminated is True
    assert result.validation is not None
    assert result.validation.valid is True

    search_outputs = [
        item.output
        for item in result.trace
        if item.role == "function_call_output"
        and item.call_id
        and item.call_id.startswith("call_search")
    ]

    assert len(search_outputs) == 2
    assert all(output is not None for output in search_outputs)
    assert all(output["hits"] for output in search_outputs)
    assert search_outputs[0]["hits"][0]["budget_id"] == "finance-saas-reference"
    assert search_outputs[0]["hits"][0]["score"] == 0.9
    assert service.commands[0].search_mode == "hybrid"
