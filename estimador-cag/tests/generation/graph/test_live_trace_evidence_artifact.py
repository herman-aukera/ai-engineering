from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

ARTIFACT_PATH = (
    PROJECT_ROOT
    / "artifacts"
    / "session13"
    / "live_postgres_logfire_trace_summary.json"
)

EXPECTED_NODE_ORDER = [
    "extract_requirements",
    "classify_components",
    "search_budgets",
    "generate_estimate",
    "validate_and_consolidate",
]


def test_live_postgres_logfire_trace_artifact() -> None:
    assert ARTIFACT_PATH.is_file()

    artifact = json.loads(
        ARTIFACT_PATH.read_text(encoding="utf-8")
    )

    assert artifact["schema_version"] == (
        "session13.live_trace_summary.v1"
    )

    execution = artifact["execution"]

    assert execution == {
        "graph_backend": "langgraph",
        "persistence_backend": "postgresql",
        "provider_backend": "deterministic_fakes",
        "telemetry_backend": "logfire_eu",
        "uses_live_postgres": True,
        "uses_live_provider": False,
        "uses_remote_logfire": True,
    }

    result = artifact["result"]

    assert result["status"] == "validated"
    assert result["review_required"] is False
    assert result["total_hours"] == 168.0
    assert result["requirement_count"] == 5
    assert result["component_count"] == 5
    assert result["budget_match_count"] == 15
    assert result["domain_trace_event_count"] == 5

    telemetry = artifact["telemetry"]

    assert telemetry["root_span_name"] == (
        "session13.graph.run"
    )
    assert telemetry["node_span_name"] == (
        "session13.graph.node"
    )
    assert telemetry["node_order"] == EXPECTED_NODE_ORDER
    assert telemetry["span_count"] == 6
    assert telemetry["root_span_count"] == 1
    assert telemetry["node_span_count"] == 5
    assert telemetry["all_spans_closed"] is True
    assert telemetry["all_nodes_share_root_trace"] is True
    assert telemetry["all_nodes_parented_to_root"] is True

    assert re.fullmatch(
        r"[0-9a-f]{32}",
        telemetry["trace_id"],
    )
    assert re.fullmatch(
        r"[0-9a-f]{16}",
        telemetry["root_span_id"],
    )

    privacy = artifact["privacy"]

    assert privacy == {
        "provider_payload_attached_to_spans": False,
        "state_payload_attached_to_spans": False,
        "token_or_dsn_recorded": False,
        "transcript_attached_to_spans": False,
    }

    assert re.fullmatch(
        r"[0-9a-f]{40}",
        artifact["execution_source_commit"],
    )

    datetime.fromisoformat(
        artifact["captured_at_utc"]
    )

    trace_lookup = artifact["trace_lookup"]

    assert trace_lookup["trace_id"] == (
        telemetry["trace_id"]
    )
    assert trace_lookup["project_url"] == (
        artifact["project_url"]
    )

    serialized = json.dumps(
        artifact,
        sort_keys=True,
    )

    for forbidden_fragment in (
        "LOGFIRE_TOKEN",
        "pylf_v1_",
        "postgresql+asyncpg://",
        "postgresql://estimator:",
    ):
        assert forbidden_fragment not in serialized
