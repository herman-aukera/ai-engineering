"""Safe observability contracts for Energy Aware Chat graph execution."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NodeSpan(BaseModel):
    """Checkpoint-safe timing and status for one actual graph node execution."""

    model_config = ConfigDict(extra="forbid")

    span_id: str = Field(min_length=1)
    node_name: str = Field(min_length=1)
    started_at_ms: int = Field(ge=0)
    finished_at_ms: int = Field(ge=0)
    status: Literal["completed", "failed"] = "completed"
    safe_error_category: str | None = Field(default=None, max_length=128)

    @property
    def duration_ms(self) -> int:
        return max(0, self.finished_at_ms - self.started_at_ms)


class GraphExecutionMetrics(BaseModel):
    """Safe aggregate derived only from authoritative graph-state records."""

    model_config = ConfigDict(extra="forbid")

    thread_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    graph_status: str
    total_wall_ms: int = Field(default=0, ge=0)
    node_count: int = Field(default=0, ge=0)
    failed_node_count: int = Field(default=0, ge=0)
    provider_call_count: int = Field(default=0, ge=0)
    provider_total_cost_usd: float = Field(default=0.0, ge=0.0)
    provider_total_latency_ms: int = Field(default=0, ge=0)
    provider_total_input_tokens: int | None = None
    provider_total_output_tokens: int | None = None
    trace_event_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    node_spans: list[NodeSpan] = Field(default_factory=list)
    safe_trace_summary: list[dict[str, str | int]] = Field(default_factory=list)


class CheckpointTelemetry(BaseModel):
    """Safe checkpoint storage statistics without checkpoint contents."""

    model_config = ConfigDict(extra="forbid")

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
    """Compute one user-safe aggregate from graph-state collections."""

    spans = list(node_spans or [])
    provider_calls = list(provider_metrics or [])
    events = list(trace_events or [])
    error_records = list(errors or [])
    safe_trace = [
        {
            "event_type": _get_attr(event, "event_type", "unknown"),
            "producer": _get_attr(event, "producer", "unknown"),
            "sequence": _get_attr(event, "sequence", 0),
        }
        for event in events
    ]
    return GraphExecutionMetrics(
        thread_id=thread_id,
        request_id=request_id,
        trace_id=trace_id,
        graph_status=graph_status,
        total_wall_ms=sum(span.duration_ms for span in spans),
        node_count=len(spans),
        failed_node_count=sum(span.status == "failed" for span in spans),
        provider_call_count=len(provider_calls),
        provider_total_cost_usd=sum(
            float(_get_attr(metric, "cost_usd", 0.0)) for metric in provider_calls
        ),
        provider_total_latency_ms=sum(
            int(_get_attr(metric, "latency_ms", 0)) for metric in provider_calls
        ),
        provider_total_input_tokens=_safe_sum_int(provider_calls, "input_tokens"),
        provider_total_output_tokens=_safe_sum_int(provider_calls, "output_tokens"),
        trace_event_count=len(events),
        error_count=len(error_records),
        node_spans=spans,
        safe_trace_summary=safe_trace,
    )


def _get_attr(obj: object, attr: str, default: object = 0) -> object:
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _safe_sum_int(items: list[object], attr: str) -> int | None:
    values = [_get_attr(item, attr, None) for item in items]
    present = [int(value) for value in values if value is not None]
    return sum(present) if present else None
