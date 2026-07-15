from __future__ import annotations

import json

import pytest

from app.generation.graph.build import REQUIRED_NODE_NAMES
from scripts.session13_generate_complex_graph_artifact import (
    SOURCE_PATH,
    build_complex_graph_artifact,
    validate_complex_graph_artifact,
)


@pytest.mark.asyncio
async def test_complex_transcript_execution_artifact(
    tmp_path,
) -> None:
    artifact = await build_complex_graph_artifact()

    validate_complex_graph_artifact(artifact)

    result = artifact["result"]
    execution = artifact["execution"]
    evidence = artifact["execution_evidence"]
    telemetry = artifact["telemetry_trace"]

    assert execution == {
        "provider_backend": "deterministic_fakes",
        "persistence_backend": "in_memory",
        "telemetry_backend": "recording_tracer",
        "telemetry_exported": False,
        "uses_live_provider": False,
        "uses_live_postgres": False,
        "uses_remote_logfire": False,
    }

    assert result["status"] == "validated"
    assert result["review_required"] is False
    assert result["errors"] == []
    assert result["estimate"]["subtotal_hours"] == 168.0
    assert result["estimate"]["contingency_hours"] == 0.0
    assert result["estimate"]["total_hours"] == 168.0
    assert result["estimate"]["total_cost_eur"] is None

    assert len(result["requirements"]) == 5
    assert len(result["components"]) == 5
    assert len(result["budget_matches"]) == 15
    assert len(result["component_estimates"]) == 5
    assert len(result["trace_events"]) == 5

    assert evidence["extractor_call_count"] == 1
    assert evidence["classifier_call_count"] == 1
    assert evidence["search_call_count"] == 5
    assert evidence["domain_node_order"] == list(
        REQUIRED_NODE_NAMES
    )
    assert evidence["telemetry_node_order"] == list(
        REQUIRED_NODE_NAMES
    )

    root_spans = [
        record
        for record in telemetry
        if record["name"] == "session13.graph.run"
    ]
    node_spans = [
        record
        for record in telemetry
        if record["name"] == "session13.graph.node"
    ]

    assert len(root_spans) == 1
    assert len(node_spans) == 5
    assert all(
        record["parent_id"]
        == root_spans[0]["record_id"]
        for record in node_spans
    )
    assert all(record["exited"] for record in telemetry)
    assert all(
        record["exception_type"] is None
        for record in telemetry
    )

    transcript = SOURCE_PATH.read_text(
        encoding="utf-8"
    )
    serialized = json.dumps(
        artifact,
        sort_keys=True,
    )

    assert transcript not in serialized

    output_path = tmp_path / "artifact.json"
    output_path.write_text(
        json.dumps(
            artifact,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    reloaded = json.loads(
        output_path.read_text(encoding="utf-8")
    )
    validate_complex_graph_artifact(reloaded)
