from __future__ import annotations

import json

import pytest

from app.energy_chat.contracts import ProjectRagRequest
from app.energy_chat.rag import retrieve_project_context
from app.energy_chat.support_rag import (
    InMemorySupportRagStore,
    SupportRagService,
    SupportRagUnavailableError,
    load_source_manifest,
)


class KeywordEmbeddingProvider:
    model = "fake-support-embedding-v1"
    _terms = ("postgresql", "docker", "spring", "health", "lock", "configuration")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [
            [float(text.casefold().count(term)) for term in self._terms]
            for text in texts
        ]


def _manifest(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "ingestion_version": "test-v1",
                "allowed_hosts": ["docs.spring.io", "www.postgresql.org"],
                "sources": [
                    {
                        "source_id": "spring-health",
                        "source_family": "spring_boot",
                        "product": "Spring Boot",
                        "product_version": "test",
                        "title": "Spring health",
                        "canonical_url": "https://docs.spring.io/spring-boot/reference/actuator/endpoints.html",
                        "support_categories": ["health"],
                    },
                    {
                        "source_id": "postgres-connections",
                        "source_family": "postgresql",
                        "product": "PostgreSQL",
                        "product_version": "test",
                        "title": "PostgreSQL connections",
                        "canonical_url": "https://www.postgresql.org/docs/current/runtime-config-connection.html",
                        "support_categories": ["database_connections"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _fetcher(url: str, allowed_hosts: tuple[str, ...]) -> str:
    assert allowed_hosts == ("docs.spring.io", "www.postgresql.org")
    if "postgresql.org" in url:
        return """
        <html><body><main><h1>Connections</h1>
        <p>PostgreSQL connection limits and connection pool exhaustion should be
        investigated with active sessions and configured connection limits.</p>
        <p>PostgreSQL connection diagnostics should distinguish server limits from
        application pool configuration.</p></main></body></html>
        """
    return """
    <html><body><main><h1>Health</h1>
    <p>Spring Boot Actuator exposes health information for application components.
    The health endpoint helps diagnose Spring application availability.</p>
    <p>Spring configuration controls which health details are exposed.</p></main></body></html>
    """


def test_support_rag_ingests_real_source_contract_and_retrieves_by_embedding(tmp_path) -> None:
    store = InMemorySupportRagStore()
    service = SupportRagService(store=store, embeddings=KeywordEmbeddingProvider())

    report = service.ingest_manifest(_manifest(tmp_path), fetcher=_fetcher)
    result = service.retrieve(
        ProjectRagRequest(query="PostgreSQL connection pool is exhausted", k=2)
    )

    assert report["sources_ingested"] == 2
    assert report["active_chunks"] >= 2
    assert result.retrieval_strategy == "openai_embedding_postgres_exact_cosine_support_rag"
    assert result.results[0].source_id == "postgres-connections"
    assert result.evidence_refs[0].startswith("source:postgres-connections:")
    assert "persisted chunks" in result.grounding_summary


def test_support_manifest_rejects_non_allowlisted_source(tmp_path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "ingestion_version": "test-v1",
                "allowed_hosts": ["docs.spring.io"],
                "sources": [
                    {
                        "source_id": "evil",
                        "source_family": "spring_boot",
                        "product": "Spring Boot",
                        "title": "Untrusted mirror",
                        "canonical_url": "https://example.com/fake-docs",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="outside the official HTTPS allowlist"):
        load_source_manifest(path)


def test_enabled_final_project_rag_never_silently_falls_back(monkeypatch) -> None:
    store = InMemorySupportRagStore()
    service = SupportRagService(store=store, embeddings=KeywordEmbeddingProvider())
    monkeypatch.setenv("EACHAT_SUPPORT_RAG_ENABLED", "true")

    import app.energy_chat.support_rag as support_rag

    monkeypatch.setattr(support_rag, "get_support_rag_service", lambda: service)

    with pytest.raises(SupportRagUnavailableError, match="no active chunks"):
        retrieve_project_context(ProjectRagRequest(query="Spring health", k=2))
