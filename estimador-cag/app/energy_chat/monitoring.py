"""Bounded, content-free monitoring aggregates for the EACHAT final project."""

from __future__ import annotations

import html
import math
from collections import Counter, deque
from dataclasses import dataclass
from threading import RLock

from pydantic import BaseModel, ConfigDict, Field


@dataclass(frozen=True)
class MonitoringSample:
    success: bool
    wall_latency_ms: int
    provider_call_count: int
    provider_cost_usd: float
    disposition: str | None


class MonitoringSnapshot(BaseModel):
    """Safe aggregate telemetry. No prompt, answer, credential, or checkpoint content."""

    model_config = ConfigDict(extra="forbid")

    sample_window: int = Field(ge=1)
    request_count: int = Field(ge=0)
    successful_request_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    error_rate: float = Field(ge=0.0, le=1.0)
    mean_latency_ms: float = Field(ge=0.0)
    p95_latency_ms: int = Field(ge=0)
    mean_provider_cost_usd: float = Field(ge=0.0)
    provider_call_count: int = Field(ge=0)
    disposition_counts: dict[str, int]


class EnergyChatMonitoringWindow:
    """Process-local rolling metrics for reviewer/demo observability."""

    def __init__(self, max_samples: int = 500) -> None:
        if max_samples <= 0:
            raise ValueError("max_samples must be positive")
        self._max_samples = max_samples
        self._samples: deque[MonitoringSample] = deque(maxlen=max_samples)
        self._lock = RLock()

    def record_success(
        self,
        *,
        wall_latency_ms: int,
        provider_call_count: int,
        provider_cost_usd: float,
        disposition: str | None,
    ) -> None:
        self._append(
            MonitoringSample(
                success=True,
                wall_latency_ms=max(0, int(wall_latency_ms)),
                provider_call_count=max(0, int(provider_call_count)),
                provider_cost_usd=max(0.0, float(provider_cost_usd)),
                disposition=(disposition or "").strip() or None,
            )
        )

    def record_error(self, *, wall_latency_ms: int) -> None:
        self._append(
            MonitoringSample(
                success=False,
                wall_latency_ms=max(0, int(wall_latency_ms)),
                provider_call_count=0,
                provider_cost_usd=0.0,
                disposition=None,
            )
        )

    def snapshot(self) -> MonitoringSnapshot:
        with self._lock:
            samples = list(self._samples)
        request_count = len(samples)
        success_count = sum(sample.success for sample in samples)
        error_count = request_count - success_count
        latencies = sorted(sample.wall_latency_ms for sample in samples)
        provider_calls = sum(sample.provider_call_count for sample in samples)
        provider_cost = sum(sample.provider_cost_usd for sample in samples)
        dispositions = Counter(
            sample.disposition for sample in samples if sample.disposition is not None
        )
        return MonitoringSnapshot(
            sample_window=self._max_samples,
            request_count=request_count,
            successful_request_count=success_count,
            error_count=error_count,
            error_rate=(error_count / request_count) if request_count else 0.0,
            mean_latency_ms=(sum(latencies) / request_count) if request_count else 0.0,
            p95_latency_ms=_percentile_nearest_rank(latencies, 0.95),
            mean_provider_cost_usd=(provider_cost / request_count) if request_count else 0.0,
            provider_call_count=provider_calls,
            disposition_counts=dict(sorted(dispositions.items())),
        )

    def _append(self, sample: MonitoringSample) -> None:
        with self._lock:
            self._samples.append(sample)


_DEFAULT_MONITORING_WINDOW = EnergyChatMonitoringWindow(max_samples=500)


def get_monitoring_window() -> EnergyChatMonitoringWindow:
    """Return the process-wide bounded monitor shared by every product chat route."""

    return _DEFAULT_MONITORING_WINDOW


def render_monitoring_dashboard(snapshot: MonitoringSnapshot) -> str:
    cards = (
        ("Requests", str(snapshot.request_count)),
        ("Success", str(snapshot.successful_request_count)),
        ("Error rate", f"{snapshot.error_rate * 100:.1f}%"),
        ("Mean latency", f"{snapshot.mean_latency_ms:.1f} ms"),
        ("P95 latency", f"{snapshot.p95_latency_ms} ms"),
        ("Mean provider cost", f"${snapshot.mean_provider_cost_usd:.6f}"),
        ("Provider calls", str(snapshot.provider_call_count)),
    )
    card_html = "".join(
        f'<div class="card"><div class="value">{html.escape(value)}</div>'
        f'<div class="label">{html.escape(label)}</div></div>'
        for label, value in cards
    )
    disposition_lines = "\n".join(
        f"{name}: {count}" for name, count in snapshot.disposition_counts.items()
    ) or "No completed dispositions in the current rolling window."
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="5">
<title>EACHAT Monitoring</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:980px;margin:2rem auto;padding:0 1rem;background:#111;color:#eee}}
h1{{margin-bottom:.2rem}}.muted{{color:#aaa}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1rem;margin:1.5rem 0}}.card{{background:#1d1d1d;border:1px solid #333;border-radius:12px;padding:1rem}}.value{{font-size:1.8rem;font-weight:700}}.label{{color:#aaa;font-size:.9rem}}pre{{background:#1d1d1d;padding:1rem;border-radius:12px;overflow:auto}}
</style>
</head>
<body>
<h1>EACHAT Final Project Monitoring</h1>
<p class="muted">Safe rolling aggregates only. Prompts, answers, credentials and checkpoint contents are not exposed. Refreshes every 5 seconds.</p>
<div class="grid">{card_html}</div>
<h2>Disposition counts</h2><pre>{html.escape(disposition_lines)}</pre>
</body>
</html>"""


def _percentile_nearest_rank(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    rank = max(1, math.ceil(percentile * len(values)))
    return values[min(rank - 1, len(values) - 1)]


__all__ = [
    "EnergyChatMonitoringWindow",
    "MonitoringSample",
    "MonitoringSnapshot",
    "get_monitoring_window",
    "render_monitoring_dashboard",
]
