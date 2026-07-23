import asyncio
import json
from pathlib import Path

from app.embedding_pipeline.search_service import SearchQueryResult, SearchResultItem
from app.generation.agentic.agent_loop import run_agent_loop_with_retrieval
from app.generation.agentic.agent_schemas import AgentRunRequest
from app.generation.agentic.retrieval_trace_artifact import write_fake_retrieval_trace_artifact


class FakeSemanticSearchService:
    async def search(self, command):
        return SearchQueryResult(
            query=command.query,
            k=command.k,
            filters_applied=command.metadata_filters.as_response_dict(),
            results=[
                SearchResultItem(
                    chunk_id=301,
                    document_id=31,
                    chunk_type="budget_component",
                    content=(
                        "Reference budget: JWT authentication includes login, "
                        "role checks, token expiry, and secure admin access."
                    ),
                    distance=0.08,
                    metadata={
                        "budget_id": "reference-finance-saas",
                        "component_id": "jwt-auth",
                        "title": "JWT authentication reference",
                    },
                ),
                SearchResultItem(
                    chunk_id=302,
                    document_id=31,
                    chunk_type="budget_component",
                    content=(
                        "Reference budget: audit logging includes sensitive actions, "
                        "exports, failed validations, and reviewer history."
                    ),
                    distance=0.15,
                    metadata={
                        "budget_id": "reference-finance-saas",
                        "component_id": "audit-logging",
                        "title": "Audit logging reference",
                    },
                ),
            ],
        )


def test_write_fake_retrieval_trace_artifact_records_non_empty_search_hits(tmp_path):
    transcript_path = Path("evals/session12_agentic/sample_transcript_complex.txt")
    output_path = tmp_path / "agent_trace_fake_retrieval_s12.json"

    result = asyncio.run(
        run_agent_loop_with_retrieval(
            AgentRunRequest(
                transcript=transcript_path.read_text(),
                provider="fake",
                max_iterations=8,
            ),
            search_service=FakeSemanticSearchService(),
            search_k=2,
        )
    )

    write_fake_retrieval_trace_artifact(
        output_path=output_path,
        scenario_id="sample_transcript_complex",
        result=result,
    )

    payload = json.loads(output_path.read_text())

    assert payload["schema_version"] == "session12.agent_trace.v1"
    assert payload["provider"] == "fake"
    assert payload["request_provider"] == "fake+retrieval"
    assert payload["terminated"] is True
    assert payload["validation"]["valid"] is True

    search_outputs = [
        item["output"]
        for item in payload["trace"]
        if item["role"] == "function_call_output"
        and item["call_id"]
        and item["call_id"].startswith("call_search")
    ]

    assert len(search_outputs) == 2
    assert all(output["hits"] for output in search_outputs)
    assert search_outputs[0]["hits"][0]["budget_id"] == "reference-finance-saas"
    assert search_outputs[0]["hits"][0]["score"] == 0.92
