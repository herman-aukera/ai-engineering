from app.schemas.estimation import DetailLevel, EstimationRequest, OutputFormat, ProjectType
from app.services.llm_service import estimate_product
from app.services.source_context import RetrievedSourceChunk


def _request() -> EstimationRequest:
    return EstimationRequest(
        description="Build a web SaaS product with payments, authentication, and admin reporting.",
        project_type=ProjectType.WEB_SAAS,
        detail_level=DetailLevel.DETAILED,
        output_format=OutputFormat.LINE_ITEMS,
    )


def _source_chunks() -> list[RetrievedSourceChunk]:
    return [
        RetrievedSourceChunk(
            chunk_id="chunk-001",
            document_id="BUDGET-2024-0001",
            content="Payments module: 24 hours",
        )
    ]


def _install_fake_provider(monkeypatch, cited_chunk_id: str) -> None:
    class FakeProvider:
        def resolve_model(self, tier):
            class Resolved:
                model = "fake-model"

            return Resolved()

        def complete_structured_messages_with_fallback(
            self,
            *,
            messages,
            starting_tier,
            tier_ladder,
            response_model,
            max_tokens,
        ):
            return {
                "result": {
                    "summary": "Generated estimate with line citations.",
                    "project_type": "web_saas",
                    "detail_level": "detailed",
                    "output_format": "line_items",
                    "total_duration_weeks": 1,
                    "total_cost_eur": 1000,
                    "confidence_pct": 80,
                    "line_items": [
                        {
                            "component": "Payments module",
                            "hours": 24,
                            "rationale": "Based on cited historical payment work.",
                            "grounded": True,
                            "sources": [
                                {
                                    "chunk_id": cited_chunk_id,
                                    "document_id": "BUDGET-2024-0001",
                                    "evidence": "Payments module: 24 hours",
                                }
                            ],
                        }
                    ],
                    "phases": [
                        {
                            "name": "Implementation",
                            "summary": "Build the cited feature.",
                            "duration_weeks": 1,
                            "cost_eur": 1000,
                            "confidence_pct": 80,
                            "tasks": ["Implement payments"],
                            "risks": [],
                        }
                    ],
                    "assumptions": [],
                    "risks": [],
                    "recommendations": [],
                },
                "tier": "flash",
                "provider": "fake",
                "model": "fake-model",
                "fallback_used": False,
            }

    class FakeCache:
        backend_name = "fake"

        def make_key(self, **kwargs):
            return "fake-key"

        def get(self, key):
            return None

        def set(self, key, value):
            return None

    monkeypatch.setattr("app.services.llm_service.LiteLLMProvider", FakeProvider)
    monkeypatch.setattr("app.services.llm_service.build_redis_cache", lambda: FakeCache())


def test_estimate_product_returns_grounded_citation_report_for_valid_citations(monkeypatch):
    _install_fake_provider(monkeypatch, cited_chunk_id="chunk-001")

    response = estimate_product(
        _request(),
        source_chunks=_source_chunks(),
        request_id="req-session11-valid",
    )

    report = response["citation_report"]

    assert report.total_lines == 1
    assert report.grounded_lines == 1
    assert report.dangling_lines == 0
    assert report.insufficient_lines == 0
    assert report.verified_citations == 1
    assert report.dangling_citations == []
    assert report.has_dangling is False


def test_estimate_product_returns_dangling_citation_report_for_invented_chunk(monkeypatch):
    _install_fake_provider(monkeypatch, cited_chunk_id="chunk-999")

    response = estimate_product(
        _request(),
        source_chunks=_source_chunks(),
        request_id="req-session11-dangling",
    )

    report = response["citation_report"]

    assert report.total_lines == 1
    assert report.grounded_lines == 0
    assert report.dangling_lines == 1
    assert report.insufficient_lines == 0
    assert report.verified_citations == 0
    assert report.dangling_citations == ["chunk-999"]
    assert report.has_dangling is True
    assert report.lines[0].status == "dangling"


def test_estimate_product_without_source_chunks_does_not_create_citation_report(monkeypatch):
    _install_fake_provider(monkeypatch, cited_chunk_id="chunk-001")

    response = estimate_product(_request())

    assert response["citation_report"] is None
