"""Milestone 14: observability — spans, metrics, and safe trace projections."""

from app.energy_chat.observability import (
    CheckpointTelemetry,
    NodeSpan,
    compute_graph_execution_metrics,
)


def test_node_span_records_timing() -> None:
    span = NodeSpan(
        span_id="span-1",
        node_name="generate_candidate",
        started_at_ms=1000,
        finished_at_ms=1234,
    )
    assert span.duration_ms == 234
    assert span.status == "completed"


def test_node_span_duration_is_non_negative() -> None:
    span = NodeSpan(
        span_id="span-2",
        node_name="run_critic_panel",
        started_at_ms=2000,
        finished_at_ms=1950,
    )
    assert span.duration_ms == 0


def test_compute_metrics_from_graph_state_fields() -> None:
    """Metrics must be computable from the primitive fields available in
    graph state without requiring live provider calls."""
    metrics = compute_graph_execution_metrics(
        thread_id="t1",
        request_id="r1",
        trace_id="tr1",
        graph_status="evaluated",
        provider_metrics=[],
        trace_events=[],
        errors=[],
        node_spans=[
            NodeSpan(
                span_id="s1",
                node_name="interpret_request",
                started_at_ms=0,
                finished_at_ms=5,
            ),
            NodeSpan(
                span_id="s2",
                node_name="generate_candidate",
                started_at_ms=5,
                finished_at_ms=42,
            ),
        ],
    )
    assert metrics.thread_id == "t1"
    assert metrics.node_count == 2
    assert metrics.total_wall_ms == 42
    assert metrics.provider_call_count == 0


def test_metrics_includes_safe_trace_summary() -> None:
    """The safe trace summary must expose event types and producers but never
    payload bodies that could contain prompts or intermediate results."""

    class FakeTraceEvent:
        def __init__(self, event_type, producer, sequence):
            self.event_type = event_type
            self.producer = producer
            self.sequence = sequence

    metrics = compute_graph_execution_metrics(
        thread_id="t1",
        request_id="r1",
        trace_id="tr1",
        graph_status="completed",
        provider_metrics=[],
        trace_events=[
            FakeTraceEvent("request_interpreted", "interpret_request", 1),
            FakeTraceEvent("candidate_generated", "generate_candidate", 2),
        ],
        errors=[],
    )
    assert metrics.trace_event_count == 2
    assert len(metrics.safe_trace_summary) == 2
    summary = metrics.safe_trace_summary[0]
    assert summary["event_type"] == "request_interpreted"
    assert summary["producer"] == "interpret_request"
    # Must not include payload
    assert "payload" not in summary


def test_metrics_aggregates_provider_costs() -> None:
    """Provider cost and latency must be aggregated across all provider calls."""

    class FakeProviderMetrics:
        def __init__(self, cost, latency, inp, out):
            self.cost_usd = cost
            self.latency_ms = latency
            self.input_tokens = inp
            self.output_tokens = out

    metrics = compute_graph_execution_metrics(
        thread_id="t1",
        request_id="r1",
        trace_id="tr1",
        graph_status="evaluated",
        provider_metrics=[
            FakeProviderMetrics(0.01, 500, 100, 50),
            FakeProviderMetrics(0.02, 300, 200, 80),
        ],
        trace_events=[],
        errors=[],
    )
    assert metrics.provider_call_count == 2
    assert metrics.provider_total_cost_usd == 0.03
    assert metrics.provider_total_latency_ms == 800
    assert metrics.provider_total_input_tokens == 300
    assert metrics.provider_total_output_tokens == 130


def test_checkpoint_telemetry_defaults() -> None:
    """Checkpoint telemetry must have safe defaults and not expose contents."""
    telemetry = CheckpointTelemetry()
    assert telemetry.total_checkpoints == 0
    assert telemetry.active_threads == 0
    assert telemetry.estimated_size_bytes == 0
    assert telemetry.oldest_checkpoint_age_minutes is None


def test_metrics_reports_error_count() -> None:
    """Error count must be derived from the errors list without exposing
    error details in the metrics summary."""
    metrics = compute_graph_execution_metrics(
        thread_id="t1",
        request_id="r1",
        trace_id="tr1",
        graph_status="failed",
        provider_metrics=[],
        trace_events=[],
        errors=[{"code": "E1"}, {"code": "E2"}, {"code": "E3"}],
    )
    assert metrics.error_count == 3
    assert metrics.graph_status == "failed"
