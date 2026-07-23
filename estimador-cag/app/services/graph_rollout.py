"""Safe graph rollout policy with non-serving shadow execution evidence."""

from __future__ import annotations

from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from threading import Lock
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

from app.config import EstimationBackend, GraphRolloutMode, TierName
from app.schemas.estimation import EstimationRequest
from app.schemas.graph_rollout import ShadowComparisonRecord
from app.services.graph_estimation import GraphEstimationApplication
from app.services.session_estimation_bridge import (
    LegacyEstimator,
    execute_session_estimation,
)

ShadowOperation = Callable[[], Awaitable[None]]


@dataclass(frozen=True)
class PreparedRollout:
    """Served response plus an optional isolated shadow operation."""

    result: dict[str, Any]
    shadow_operation: ShadowOperation | None = None


class InMemoryGraphShadowStore:
    """Thread-safe bounded ledger for recent sanitized shadow comparisons."""

    def __init__(self, *, max_records: int = 100) -> None:
        if max_records <= 0:
            raise ValueError("max_records must be positive")
        self._records: deque[ShadowComparisonRecord] = deque(maxlen=max_records)
        self._lock = Lock()

    def append(self, record: ShadowComparisonRecord) -> None:
        with self._lock:
            self._records.append(record)

    def list(self, *, limit: int = 20) -> list[ShadowComparisonRecord]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        with self._lock:
            records = list(self._records)
        return list(reversed(records[-limit:]))

    def reset(self) -> None:
        with self._lock:
            self._records.clear()


GLOBAL_GRAPH_SHADOW_STORE = InMemoryGraphShadowStore()


def _request_fingerprint(*, transcript: str, attachments_text: str) -> str:
    raw = f"{transcript}\x00{attachments_text}".encode()
    return sha256(raw).hexdigest()


def _mapping(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _legacy_cost(result: dict[str, Any]) -> float | None:
    value = _mapping(result.get("result")).get("total_cost_eur")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(0.0, float(value))
    return None


def _graph_payload(result: dict[str, Any]) -> dict[str, Any]:
    return _mapping(result.get("graph_estimation"))


def _graph_cost(result: dict[str, Any]) -> float | None:
    value = _mapping(_graph_payload(result).get("estimate")).get("total_cost_eur")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(0.0, float(value))
    return None


def _cost_delta(primary_cost: float | None, shadow_cost: float | None) -> float | None:
    if primary_cost is None or shadow_cost is None:
        return None
    return round(shadow_cost - primary_cost, 2)


def _completed_record(
    *,
    comparison_id: UUID,
    created_at: datetime,
    fingerprint: str,
    session_id: str | None,
    primary_result: dict[str, Any],
    shadow_result: dict[str, Any],
    primary_latency_ms: int,
    shadow_latency_ms: int,
) -> ShadowComparisonRecord:
    graph_payload = _graph_payload(shadow_result)
    primary_cost = _legacy_cost(primary_result)
    shadow_cost = _graph_cost(shadow_result)
    return ShadowComparisonRecord(
        comparison_id=comparison_id,
        created_at=created_at,
        status="completed",
        request_fingerprint=fingerprint,
        session_id=session_id,
        primary_latency_ms=primary_latency_ms,
        shadow_latency_ms=shadow_latency_ms,
        latency_delta_ms=shadow_latency_ms - primary_latency_ms,
        primary_total_cost_eur=primary_cost,
        shadow_total_cost_eur=shadow_cost,
        cost_delta_eur=_cost_delta(primary_cost, shadow_cost),
        primary_text_chars=len(str(primary_result.get("text") or "")),
        shadow_text_chars=len(str(shadow_result.get("text") or "")),
        primary_structured_result=primary_result.get("result") is not None,
        shadow_graph_status=(
            str(graph_payload["status"])
            if graph_payload.get("status") is not None
            else None
        ),
        shadow_review_required=(
            bool(graph_payload["review_required"])
            if graph_payload.get("review_required") is not None
            else None
        ),
    )


def _failed_record(
    *,
    comparison_id: UUID,
    created_at: datetime,
    fingerprint: str,
    session_id: str | None,
    primary_result: dict[str, Any],
    primary_latency_ms: int,
    shadow_latency_ms: int,
    error: Exception,
) -> ShadowComparisonRecord:
    return ShadowComparisonRecord(
        comparison_id=comparison_id,
        created_at=created_at,
        status="failed",
        request_fingerprint=fingerprint,
        session_id=session_id,
        primary_latency_ms=primary_latency_ms,
        shadow_latency_ms=shadow_latency_ms,
        latency_delta_ms=shadow_latency_ms - primary_latency_ms,
        primary_total_cost_eur=_legacy_cost(primary_result),
        primary_text_chars=len(str(primary_result.get("text") or "")),
        shadow_text_chars=0,
        primary_structured_result=primary_result.get("result") is not None,
        error_type=type(error).__name__,
        error_message=str(error)[:500],
    )


async def _execute_backend(
    *,
    backend: EstimationBackend,
    legacy_estimator: LegacyEstimator,
    graph_service: GraphEstimationApplication | None,
    request: EstimationRequest,
    transcript: str,
    tier: TierName | None,
    prompt_version: str,
    project_metadata: object,
    attachments_text: str,
    conversation_history: list[dict[str, str]],
) -> dict[str, Any]:
    return await execute_session_estimation(
        backend=backend,
        legacy_estimator=legacy_estimator,
        graph_service=graph_service,
        request=request,
        transcript=transcript,
        tier=tier,
        prompt_version=prompt_version,
        project_metadata=project_metadata,
        attachments_text=attachments_text,
        conversation_history=conversation_history,
    )


async def prepare_session_estimation_rollout(
    *,
    rollout_mode: GraphRolloutMode,
    configured_backend: EstimationBackend,
    legacy_estimator: LegacyEstimator,
    graph_service: GraphEstimationApplication | None,
    request: EstimationRequest,
    transcript: str,
    tier: TierName | None,
    prompt_version: str,
    project_metadata: object,
    attachments_text: str,
    conversation_history: list[dict[str, str]],
    shadow_store: InMemoryGraphShadowStore = GLOBAL_GRAPH_SHADOW_STORE,
    session_id: str | None = None,
) -> PreparedRollout:
    """Prepare one served result and optionally one isolated graph shadow run."""

    common = {
        "legacy_estimator": legacy_estimator,
        "graph_service": graph_service,
        "request": request,
        "transcript": transcript,
        "tier": tier,
        "prompt_version": prompt_version,
        "project_metadata": project_metadata,
        "attachments_text": attachments_text,
        "conversation_history": conversation_history,
    }

    if rollout_mode in {"off", "serve"}:
        backend: EstimationBackend = (
            "graph" if rollout_mode == "serve" else configured_backend
        )
        result = await _execute_backend(backend=backend, **common)
        result["graph_rollout_mode"] = rollout_mode
        return PreparedRollout(result=result)

    primary_started = perf_counter()
    primary_result = await _execute_backend(backend="legacy", **common)
    primary_latency_ms = int((perf_counter() - primary_started) * 1000)
    comparison_id = uuid4()
    created_at = datetime.now(UTC)
    fingerprint = _request_fingerprint(
        transcript=transcript,
        attachments_text=attachments_text,
    )
    primary_result["graph_rollout_mode"] = "shadow"
    primary_result["shadow_comparison_id"] = str(comparison_id)

    async def shadow_operation() -> None:
        shadow_started = perf_counter()
        try:
            shadow_result = await _execute_backend(backend="graph", **common)
        except Exception as exc:
            shadow_latency_ms = int((perf_counter() - shadow_started) * 1000)
            shadow_store.append(
                _failed_record(
                    comparison_id=comparison_id,
                    created_at=created_at,
                    fingerprint=fingerprint,
                    session_id=session_id,
                    primary_result=primary_result,
                    primary_latency_ms=primary_latency_ms,
                    shadow_latency_ms=shadow_latency_ms,
                    error=exc,
                )
            )
            return

        shadow_latency_ms = int((perf_counter() - shadow_started) * 1000)
        shadow_store.append(
            _completed_record(
                comparison_id=comparison_id,
                created_at=created_at,
                fingerprint=fingerprint,
                session_id=session_id,
                primary_result=primary_result,
                shadow_result=shadow_result,
                primary_latency_ms=primary_latency_ms,
                shadow_latency_ms=shadow_latency_ms,
            )
        )

    return PreparedRollout(
        result=primary_result,
        shadow_operation=shadow_operation,
    )
