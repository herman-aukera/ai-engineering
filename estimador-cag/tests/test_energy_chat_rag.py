from __future__ import annotations

from app.energy_chat.contracts import ProjectRagRequest
from app.energy_chat.rag import retrieve_project_context


def test_project_rag_retrieves_final_project_requirements() -> None:
    result = retrieve_project_context(
        ProjectRagRequest(
            query="Which final project deliverables need RAG, agents, evals, and deployment?",
            k=3,
        )
    )

    assert result.retrieval_strategy == "deterministic_lexical_cosine_project_rag"
    assert result.results
    assert result.results[0].source_id == "final_project_requirements"
    assert "source:final_project_requirements" in result.evidence_refs
    assert "CI-safe RAG baseline" in result.grounding_summary


def test_project_rag_retrieves_provider_fallback_source() -> None:
    result = retrieve_project_context(
        ProjectRagRequest(
            query="DeepSeek should use Kimi backup provider routing when the primary fails",
            k=6,
        )
    )

    source_ids = {chunk.source_id for chunk in result.results}
    assert "provider_fallback" in source_ids
    assert all(chunk.score >= 0.0 for chunk in result.results)
    assert len(result.results) == 6
