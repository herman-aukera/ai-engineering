from app.prompts.loader import render_estimation_prompt
from app.schemas.estimation import DetailLevel, EstimationRequest, OutputFormat, ProjectType
from app.services.llm_service import _build_structured_product_system_prompt, estimate_product
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


def test_structured_product_system_prompt_includes_line_citation_rules_when_enabled():
    system_prompt = _build_structured_product_system_prompt(
        prompt_version="v1",
        include_line_citation_rules=True,
    )

    assert "Line-level citation rules:" in system_prompt
    assert "Every grounded line must cite one or more exact source id values" in system_prompt
    assert "chunk_id must be copied exactly from the source id attribute" in system_prompt
    assert "document_id must be copied exactly from the source document_id attribute" in system_prompt
    assert "evidence must be a verbatim span or figure from the cited source" in system_prompt
    assert "Do not cite chunk ids that are not present in retrieved_context" in system_prompt


def test_structured_product_system_prompt_omits_line_citation_rules_by_default():
    system_prompt = _build_structured_product_system_prompt(prompt_version="v1")

    assert "Line-level citation rules:" not in system_prompt


def test_rendered_user_prompt_contains_source_context_for_source_chunks():
    _, user_prompt = render_estimation_prompt(
        _request(),
        version="v1",
        source_chunks=_source_chunks(),
    )

    assert '<source id="chunk-001" document_id="BUDGET-2024-0001">' in user_prompt
    assert "Payments module: 24 hours" in user_prompt
    assert "</retrieved_context>" in user_prompt


def test_estimate_product_accepts_source_chunks_argument(monkeypatch):
    captured: dict[str, object] = {}

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
            captured["messages"] = messages

            return {
                "result": {
                    "summary": "Grounded estimate.",
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
                                    "chunk_id": "chunk-001",
                                    "document_id": "BUDGET-2024-0001",
                                    "evidence": "Payments module: 24 hours",
                                }
                            ],
                        }
                    ],
                    "phases": [
                        {
                            "name": "Implementation",
                            "summary": "Build the core feature.",
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

    response = estimate_product(
        _request(),
        source_chunks=_source_chunks(),
    )

    assert response["result"].line_items[0].sources[0].chunk_id == "chunk-001"

    messages = captured["messages"]
    system_message = messages[0]["content"]
    user_message = messages[-1]["content"]

    assert "Line-level citation rules:" in system_message
    assert '<source id="chunk-001" document_id="BUDGET-2024-0001">' in user_message
