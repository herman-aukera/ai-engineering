from __future__ import annotations

import json

from app.energy_chat.candidate_provider import (
    CandidateGenerationResult,
    CandidateProviderRequest,
)
from app.energy_chat.graph_runtime import run_energy_chat_graph
from app.energy_chat.graph_state import EnergyChatGraphState, ProviderMetrics
from app.energy_chat.support_rag import InMemorySupportRagStore, SupportRagService


class KeywordEmbeddingProvider:
    model = "fake-support-embedding-v1"
    _terms = ("postgresql", "connection", "sessions", "limit")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [
            [float(text.casefold().count(term)) for term in self._terms]
            for text in texts
        ]


class EvidenceAwareAnswerProvider:
    def generate(self, request: CandidateProviderRequest) -> CandidateGenerationResult:
        assert request.evidence_refs
        return CandidateGenerationResult(
            answer=(
                "PostgreSQL documentation provides bounded evidence for checking connection "
                "limits and active sessions before attributing the failure to one cause. "
                "Compare those server observations with the application pool configuration. "
                "Next action: collect the connection error and inspect the documented limits."
            ),
            evidence_refs=request.evidence_refs,
            metrics=ProviderMetrics(
                provider_call_id=request.provider_call_id,
                provider="fake",
                model="final-project-rag-graph-v1",
                tier="local",
            ),
        )


def test_final_project_support_rag_evidence_reaches_authoritative_graph(
    tmp_path, monkeypatch
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "ingestion_version": "graph-test-v1",
                "allowed_hosts": ["www.postgresql.org"],
                "sources": [
                    {
                        "source_id": "postgres-connections",
                        "source_family": "postgresql",
                        "product": "PostgreSQL",
                        "product_version": "test",
                        "title": "PostgreSQL connections",
                        "canonical_url": "https://www.postgresql.org/docs/current/runtime-config-connection.html",
                        "support_categories": ["database_connections"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    def fetcher(url: str, allowed_hosts: tuple[str, ...]) -> str:
        assert url.startswith("https://www.postgresql.org/")
        assert allowed_hosts == ("www.postgresql.org",)
        return """
        <html><body><main><h1>Connections</h1>
        <p>PostgreSQL connection limits constrain concurrent sessions and should be
        compared with active sessions when diagnosing connection exhaustion.</p>
        <p>Application connection pool settings should be evaluated against the
        configured PostgreSQL server limits before assigning a root cause.</p>
        </main></body></html>
        """

    store = InMemorySupportRagStore()
    service = SupportRagService(store=store, embeddings=KeywordEmbeddingProvider())
    service.ingest_manifest(manifest, fetcher=fetcher)

    monkeypatch.setenv("EACHAT_SUPPORT_RAG_ENABLED", "true")
    import app.energy_chat.support_pgvector as support_pgvector

    monkeypatch.setattr(
        support_pgvector,
        "get_pgvector_support_rag_service",
        lambda: service,
    )

    state = run_energy_chat_graph(
        EnergyChatGraphState(
            thread_id="final-project-rag-thread",
            request_id="final-project-rag-request",
            trace_id="final-project-rag-trace",
            user_request=(
                "PostgreSQL connections are exhausted. Which connection limits and "
                "session evidence should I inspect?"
            ),
            mode="project",
            policy_version="unresolved",
        ),
        provider=EvidenceAwareAnswerProvider(),
    )

    assert state.project_rag is not None
    assert state.project_rag.retrieval_strategy == "openai_embedding_postgres_exact_cosine_support_rag"
    assert state.project_rag.results[0].source_id == "postgres-connections"
    assert state.evidence_refs
    assert state.candidate_versions[-1].evidence_refs == state.evidence_refs
    assert state.decision_outcomes[-1].disposition == "accept"
