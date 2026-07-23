from __future__ import annotations

import json

import pytest

from app.ui.graph_inspector import (
    GRAPH_NODE_ORDER,
    build_execution_header,
    build_graph_request_payload,
    build_graphviz_source,
    build_provenance_rows,
    build_timeline_rows,
    parse_graph_payload,
)


def _payload() -> dict:
    return {
        "estimation_id": "11111111-1111-4111-8111-111111111111",
        "thread_id": "estimate:11111111-1111-4111-8111-111111111111",
        "graph_version": "session13.v1",
        "status": "needs_review",
        "review_required": True,
        "estimate": {
            "components": [],
            "subtotal_hours": 40.0,
            "contingency_hours": 4.0,
            "total_hours": 44.0,
            "total_cost_eur": 4400.0,
            "currency": "EUR",
        },
        "requirements": [],
        "components": [],
        "budget_matches": [
            {
                "component_id": "cmp-auth",
                "budget_id": "BUD-101",
                "reference_component_id": "ref-auth",
                "source_document_id": "DOC-10",
                "source_chunk_id": "CH-101",
                "recorded_hours": 36.0,
                "distance": 0.09,
                "score": 0.91,
                "retrieval_method": "hybrid",
            },
            {
                "component_id": "cmp-auth",
                "budget_id": "BUD-202",
                "reference_component_id": "ref-auth-2",
                "source_document_id": "DOC-20",
                "source_chunk_id": "CH-202",
                "recorded_hours": 44.0,
                "distance": 0.12,
                "score": 0.88,
                "retrieval_method": "hybrid",
            },
        ],
        "component_estimates": [
            {
                "component_id": "cmp-auth",
                "name": "JWT authentication",
                "hours": 40.0,
                "grounding_status": "conflict",
                "reference_budget_ids": ["BUD-101", "BUD-202"],
                "reference_component_ids": ["ref-auth", "ref-auth-2"],
                "source_hours": [36.0, 44.0],
                "source_range_low": 36.0,
                "source_range_high": 44.0,
                "dispersion": 8.0,
                "confidence": 0.84,
                "derivation_method": "median_recorded_hours",
                "review_reasons": ["source spread requires review"],
            }
        ],
        "errors": [],
        "trace_events": [
            {
                "event_type": "requirements_extracted",
                "node": "extract_requirements",
                "summary": "Extracted two atomic requirements.",
                "evidence_refs": [],
                "state_delta_keys": ["requirements"],
            },
            {
                "event_type": "components_classified",
                "node": "classify_components",
                "summary": "Classified one authentication component.",
                "evidence_refs": ["req-1", "req-2"],
                "state_delta_keys": ["components"],
            },
            {
                "event_type": "component_estimated",
                "node": "generate_estimate",
                "summary": "Calculated the deterministic median.",
                "evidence_refs": ["CH-101", "CH-202"],
                "state_delta_keys": ["component_estimates", "estimate"],
            },
        ],
        "provider_metadata": {
            "provider": "deepseek",
            "model": "deepseek-v4-flash",
            "prompt_version": "session13.v1",
        },
        "execution_metadata": {
            "requirement_count": 2,
            "component_count": 1,
            "budget_match_count": 2,
            "component_estimate_count": 1,
            "graph_version": "session13.v1",
        },
    }


def test_build_graph_request_payload_omits_empty_estimation_id() -> None:
    assert build_graph_request_payload(
        transcript="  Build a secure onboarding platform.  ",
        estimation_id="  ",
    ) == {"transcript": "Build a secure onboarding platform."}


def test_parse_graph_payload_rejects_non_object_json() -> None:
    with pytest.raises(ValueError, match="must be a JSON object"):
        parse_graph_payload(json.dumps(["not", "an", "object"]))


def test_execution_header_exposes_safe_control_room_metrics() -> None:
    header = build_execution_header(_payload())

    assert header["status"] == "needs_review"
    assert header["review_required"] is True
    assert header["total_hours"] == 44.0
    assert header["total_cost_eur"] == 4400.0
    assert header["provider"] == "deepseek"
    assert header["budget_match_count"] == 2


def test_timeline_keeps_graph_order_and_marks_unobserved_nodes() -> None:
    rows = build_timeline_rows(_payload())

    assert [row["node"] for row in rows[:5]] == list(GRAPH_NODE_ORDER)
    assert rows[0]["status"] == "completed"
    assert rows[1]["status"] == "completed"
    assert rows[2]["status"] == "not_observed"
    assert rows[3]["status"] == "completed"
    assert rows[3]["state_keys_changed"] == "component_estimates, estimate"
    assert rows[3]["evidence_refs"] == "CH-101, CH-202"


def test_provenance_rows_join_component_estimate_to_all_sources() -> None:
    rows = build_provenance_rows(_payload())

    assert rows == [
        {
            "component_id": "cmp-auth",
            "component": "JWT authentication",
            "hours": 40.0,
            "grounding_status": "conflict",
            "confidence_pct": 84,
            "derivation_method": "median_recorded_hours",
            "source_range_low": 36.0,
            "source_range_high": 44.0,
            "reference_count": 2,
            "budget_ids": "BUD-101, BUD-202",
            "source_documents": "DOC-10, DOC-20",
            "source_chunks": "CH-101, CH-202",
            "review_reasons": "source spread requires review",
        }
    ]


def test_graphviz_source_contains_stable_topology_and_observed_status() -> None:
    source = build_graphviz_source(_payload())

    assert '"START" -> "extract_requirements"' in source
    assert '"extract_requirements" [label="extract_requirements\\ncompleted"]' in source
    assert '"search_budgets" [label="search_budgets\\nnot_observed"]' in source
    assert '"validate_and_consolidate" -> "END"' in source
