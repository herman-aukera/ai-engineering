from __future__ import annotations

from app.services.graph_estimation import GraphEstimationRun
from app.services.graph_product_adapter import adapt_graph_run_to_product_response


def _graph_run(*, needs_review: bool = False) -> GraphEstimationRun:
    status = "needs_review" if needs_review else "validated"
    component_estimate = {
        "component_id": "component-1",
        "name": "API implementation",
        "hours": 48.0,
        "grounding_status": "grounded",
        "reference_budget_ids": ["budget-1"],
        "reference_component_ids": ["reference-1"],
        "source_hours": [40.0, 56.0],
        "source_range_low": 40.0,
        "source_range_high": 56.0,
        "dispersion": 16.0,
        "confidence": 0.8,
        "derivation_method": "median",
        "review_reasons": [],
    }
    return GraphEstimationRun(
        estimation_id="12345678-1234-5678-1234-567812345678",
        thread_id="estimate:12345678-1234-5678-1234-567812345678",
        state={
            "graph_version": "session13.v1",
            "status": status,
            "review_required": needs_review,
            "requirements": [
                {
                    "requirement_id": "requirement-1",
                    "text": "Build an authenticated API",
                }
            ],
            "components": [
                {
                    "component_id": "component-1",
                    "name": "API implementation",
                    "category": "backend",
                    "requirement_ids": ["requirement-1"],
                }
            ],
            "budget_matches": [
                {
                    "component_id": "component-1",
                    "budget_id": "budget-1",
                    "reference_component_id": "reference-1",
                    "source_document_id": "document-1",
                    "source_chunk_id": "chunk-1",
                    "recorded_hours": 48.0,
                    "distance": 0.1,
                    "score": 0.9,
                    "retrieval_method": "hybrid",
                }
            ],
            "component_estimates": [component_estimate],
            "estimate": {
                "components": [component_estimate],
                "subtotal_hours": 48.0,
                "contingency_hours": 4.8,
                "total_hours": 52.8,
                "total_cost_eur": 5280.0,
                "currency": "EUR",
            },
            "errors": [],
            "trace_events": [
                {
                    "event_type": "estimate_validated",
                    "node": "validate_and_consolidate",
                    "summary": "Estimate validated",
                    "evidence_refs": ["budget-1"],
                    "state_delta_keys": ["estimate", "status"],
                }
            ],
            "provider_metadata": {
                "provider": "deterministic-fake",
                "model": "fake-model",
                "prompt_version": "graph-v1",
            },
            "execution_metadata": {
                "requirement_count": 1,
                "component_count": 1,
                "budget_match_count": 1,
                "component_estimate_count": 1,
                "graph_version": "session13.v1",
            },
        },
    )


def test_adapter_preserves_graph_evidence_without_inventing_legacy_result() -> None:
    response = adapt_graph_run_to_product_response(
        _graph_run(),
        requested_prompt_version="v2",
        requested_tier="flash",
    )

    assert response["estimation_backend"] == "graph"
    assert response["result"] is None
    assert response["prompt_version"] == "graph-v1"
    assert response["requested_prompt_version"] == "v2"
    assert response["requested_tier"] == "flash"
    assert response["compatibility"] == {
        "mode": "graph_text_fallback",
        "parity": "partial",
        "legacy_structured_result": False,
        "reason": (
            "The graph exposes component hours and provenance, while the "
            "legacy product contract requires phases, duration, and confidence."
        ),
    }

    graph_payload = response["graph_estimation"]
    assert graph_payload["estimate"]["total_hours"] == 52.8
    assert graph_payload["estimate"]["total_cost_eur"] == 5280.0
    assert graph_payload["budget_matches"][0]["source_chunk_id"] == "chunk-1"
    assert "52.8" in response["text"]
    assert "API implementation: 48 hours" in response["text"]


def test_adapter_exposes_review_state_without_claiming_structured_parity() -> None:
    response = adapt_graph_run_to_product_response(
        _graph_run(needs_review=True),
        requested_prompt_version="v1",
        requested_tier=None,
    )

    assert response["graph_estimation"]["status"] == "needs_review"
    assert response["graph_estimation"]["review_required"] is True
    assert response["result"] is None
    assert "Review required: yes" in response["text"]
