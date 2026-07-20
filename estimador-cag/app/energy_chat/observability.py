"""Observability contracts for Energy Aware Chat — spans, metrics, and safe dashboards.

Milestone 14: typed NodeSpans for per-node timing, GraphExecutionMetrics for
aggregation, and safe trace projections that exclude secrets, prompts,
and raw provider transcripts.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class NodeSpan(BaseModel):
    """Wall-clock timing and status for one graph node execution.

    Stored in graph state so replay and audit can reconstruct execution
    timelines without accessing external monitoring systems.
    """

    span_id: str = Field(min_length=1)
    node_name: str = Field(min_length=1)
    started_at_ms: int = Field(ge=0)
    finished_at_ms: int = Field(ge=0)
    status: str = "completed"

    @property
    def duration_ms(self) -> int:
        return max(0, self.finished_at_ms - self.started_at_ms)


class GraphExecutionMetrics(BaseModel):
    """Aggregated observability facts derived from authoritative graph state.

    All values come from domain-owned records (trace events, provider metrics,
    node spans). No external monitoring system is required as the source of truth.
    """

    thread_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    graph_status: str
    total_wall_ms: int = Field(default=0, ge=0)
    node_count: int = Field(default=0, ge=0)
    provider_call_count: int = Field(default=0, ge=0)
    provider_total_cost_usd: float = Field(default=0.0, ge=0.0)
    provider_total_latency_ms: int = Field(default=0, ge=0)
    provider_total_input_tokens: int | None = None
    provider_total_output_tokens: int | None = None
    trace_event_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    node_spans: list[NodeSpan] = Field(default_factory=list)
    safe_trace_summary: list[dict[str, str | int]] = Field(
        default_factory=list,
        description="Event types and producers only; no payload bodies exposed",
    )


class CheckpointTelemetry(BaseModel):
    """Safe checkpoint storage statistics for operational monitoring.

    Does not expose checkpoint contents, thread data, or user information.
    """

    total_checkpoints: int = Field(default=0, ge=0)
    active_threads: int = Field(default=0, ge=0)
    estimated_size_bytes: int = Field(default=0, ge=0)
    oldest_checkpoint_age_minutes: int | None = None


def compute_graph_execution_metrics(
    *,
    thread_id: str,
    request_id: str,
    trace_id: str,
    graph_status: str,
    provider_metrics: list[object],
    trace_events: list[object],
    errors: list[object],
    node_spans: list[NodeSpan] | None = None,
) -> GraphExecutionMetrics:
    """Compute aggregated metrics from authoritative graph state records.

    Provider metrics and trace events are read from domain state. No external
    system calls, secret fields, or raw transcripts are included.
    """

    spans = list(node_spans) if node_spans else []
    total_wall_ms = _sum_attr(spans, "duration_ms")

    provider_calls = list(provider_metrics) if provider_metrics else []
    total_cost = sum(_get_attr(m, "cost_usd", 0.0) for m in provider_calls)
    total_latency = sum(_get_attr(m, "latency_ms", 0) for m in provider_calls)
    total_input = _safe_sum_int(provider_calls, "input_tokens")
    total_output = _safe_sum_int(provider_calls, "output_tokens")

    safe_trace = [
        {
            "event_type": _get_attr(e, "event_type", "unknown"),
            "producer": _get_attr(e, "producer", "unknown"),
            "sequence": _get_attr(e, "sequence", 0),
        }
        for e in (list(trace_events) if trace_events else [])
    ]

    return GraphExecutionMetrics(
        thread_id=thread_id,
        request_id=request_id,
        trace_id=trace_id,
        graph_status=graph_status,
        total_wall_ms=total_wall_ms,
        node_count=len(spans),
        provider_call_count=len(provider_calls),
        provider_total_cost_usd=total_cost,
        provider_total_latency_ms=total_latency,
        provider_total_input_tokens=total_input,
        provider_total_output_tokens=total_output,
        trace_event_count=len(list(trace_events) if trace_events else []),
        error_count=len(list(errors) if errors else []),
        node_spans=spans,
        safe_trace_summary=safe_trace,
    )


def _sum_attr(items: list[object], attr: str) -> int:
    return sum(_get_attr(item, attr, 0) for item in items)


def _get_attr(obj: object, attr: str, default: object = 0) -> object:
    return getattr(obj, attr, default) if hasattr(obj, attr) else default


def _safe_sum_int(items: list[object], attr: str) -> int | None:
    total = 0
    any_present = False
    for item in items:
        val = getattr(item, attr, None)
        if val is not None:
            total += int(val)
            any_present = True
    return total if any_present else None
