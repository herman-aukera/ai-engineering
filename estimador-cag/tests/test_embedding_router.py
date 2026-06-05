from __future__ import annotations

from fastapi.testclient import TestClient

import app.embedding_pipeline.router as embedding_router_module
from app.embedding_pipeline.embedder import EMBEDDING_MODEL
from app.embedding_pipeline.schemas import EmbeddedChunk
from app.main import app


def sample_budget_payload() -> dict:
    return {
        "budget_id": "BUD-2024-014",
        "client_metadata": {
            "name": "FintechCorp",
            "sector": "finance",
            "country": "ES",
        },
        "project_summary": "Mobile banking API with OAuth 2.0 authentication and PSD2 compliance",
        "main_technology": "ruby_on_rails",
        "year": 2024,
        "total_estimated_hours": 480,
        "components": [
            {
                "component_id": "AUTH-001",
                "name": "OAuth 2.0 authentication backend",
                "description": (
                    "Implementation of OAuth 2.0 flows with JWT-based session management, "
                    "multi-tenant token isolation, and rate limiting per client."
                ),
                "tech_stack": ["ruby_on_rails", "postgresql", "redis"],
                "estimated_hours": 120,
                "complexity": "high",
                "dependencies": [],
            },
            {
                "component_id": "AUDIT-001",
                "name": "Audit logging",
                "description": "Immutable audit trail for regulated account operations.",
                "tech_stack": ["ruby_on_rails", "postgresql"],
                "estimated_hours": 80,
                "complexity": "medium",
                "dependencies": ["AUTH-001"],
            },
        ],
    }


class FakeEmbedder:
    def embed_many(self, chunks):
        return [
            EmbeddedChunk(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                metadata=chunk.metadata,
                token_count=chunk.token_count,
                embedding=[float(index), float(index + 1)],
            )
            for index, chunk in enumerate(chunks)
        ]


class FailingEmbedder:
    def embed_many(self, chunks):
        raise RuntimeError("provider exploded with internal details")


def test_embeddings_ingest_returns_vectorized_chunks_and_stats(monkeypatch) -> None:
    monkeypatch.setattr(embedding_router_module, "OpenAIEmbedder", FakeEmbedder)

    client = TestClient(app)
    response = client.post(
        "/embeddings/ingest",
        json={"budgets": [sample_budget_payload()]},
    )

    assert response.status_code == 200
    body = response.json()

    assert [chunk["chunk_id"] for chunk in body["chunks"]] == [
        "BUD-2024-014::AUTH-001",
        "BUD-2024-014::AUDIT-001",
    ]
    assert body["chunks"][0]["embedding"] == [0.0, 1.0]
    assert body["chunks"][1]["embedding"] == [1.0, 2.0]
    assert body["chunks"][0]["metadata"]["client_sector"] == "finance"

    stats = body["stats"]
    assert stats["total_budgets"] == 1
    assert stats["total_chunks"] == 2
    assert stats["total_tokens"] > 0
    assert stats["estimated_cost_usd"] > 0
    assert stats["model"] == EMBEDDING_MODEL


def test_embeddings_ingest_uses_pydantic_validation() -> None:
    client = TestClient(app)

    response = client.post("/embeddings/ingest", json={"budgets": []})

    assert response.status_code == 422


def test_embeddings_ingest_returns_generic_500_for_embedder_errors(monkeypatch) -> None:
    monkeypatch.setattr(embedding_router_module, "OpenAIEmbedder", FailingEmbedder)

    client = TestClient(app)
    response = client.post(
        "/embeddings/ingest",
        json={"budgets": [sample_budget_payload()]},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Embedding ingestion failed"}



def test_embeddings_compare_returns_strategy_rankings() -> None:
    client = TestClient(app)

    response = client.post(
        "/embeddings/compare",
        json={
            "budgets": [sample_budget_payload()],
            "query": "OAuth JWT authentication banking authorization",
            "top_k": 1,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["query"] == "OAuth JWT authentication banking authorization"
    assert body["top_k"] == 1

    by_name = {strategy["strategy_name"]: strategy for strategy in body["strategies"]}

    assert set(by_name) == {"structural_component", "whole_budget"}

    structural_top = by_name["structural_component"]["top_chunks"][0]
    whole_budget_top = by_name["whole_budget"]["top_chunks"][0]

    assert structural_top["rank"] == 1
    assert structural_top["chunk_id"] == "BUD-2024-014::AUTH-001"
    assert structural_top["score"] > 0

    assert whole_budget_top["rank"] == 1
    assert whole_budget_top["chunk_id"] == "BUD-2024-014::whole_budget"
    assert whole_budget_top["score"] > 0


def test_embeddings_compare_rejects_invalid_top_k() -> None:
    client = TestClient(app)

    response = client.post(
        "/embeddings/compare",
        json={
            "budgets": [sample_budget_payload()],
            "query": "OAuth",
            "top_k": 0,
        },
    )

    assert response.status_code == 422


def test_embeddings_compare_is_registered_in_openapi() -> None:
    client = TestClient(app)

    schema = client.get("/openapi.json").json()

    assert "/embeddings/compare" in schema["paths"]
