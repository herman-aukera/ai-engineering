"""Self-contained canonical V2 transport for the EACHAT production service."""

from __future__ import annotations

from time import perf_counter

from fastapi import APIRouter, HTTPException, Path, Request
from fastapi.responses import HTMLResponse

from app.energy_chat.api_v2_contracts import (
    EnergyChatV2Request,
    EnergyChatV2Response,
    EnergyChatV2ThreadStateResponse,
    ExecutionProfile,
    ProviderUnavailableError,
    UnsupportedProfileError,
)
from app.energy_chat.candidate_provider import ProviderBudgetExceededError
from app.energy_chat.graph_application import build_v2_error_detail
from app.energy_chat.monitoring import (
    MonitoringSnapshot,
    get_monitoring_window,
    render_monitoring_dashboard,
)
from app.energy_chat.ownership_http import assert_resource_owner, claim_resource
from app.energy_chat.runtime_container import (
    EnergyChatApplicationRuntime,
    ThreadCheckpointConflictError,
    ThreadCheckpointNotFoundError,
)
from app.energy_chat.settings import energy_chat_v2_enabled

router = APIRouter()
_MONITORING = get_monitoring_window()


def _require_v2_enabled() -> None:
    if not energy_chat_v2_enabled():
        raise HTTPException(
            status_code=404,
            detail={
                "error": "v2_disabled",
                "detail": "Energy Chat V2 is disabled by EACHAT_V2_ENABLED.",
            },
        )


def _application_runtime(request: Request) -> EnergyChatApplicationRuntime:
    runtime = getattr(request.app.state, "energy_chat_runtime", None)
    if not isinstance(runtime, EnergyChatApplicationRuntime):
        raise RuntimeError("Energy Chat application runtime is not configured")
    return runtime


def _bind_route_profile(
    request: EnergyChatV2Request,
    expected: ExecutionProfile,
) -> EnergyChatV2Request:
    if request.execution_profile is not None and request.execution_profile != expected:
        raise UnsupportedProfileError(
            field="execution_profile",
            value=request.execution_profile,
            detail=(
                f"Execution profile '{request.execution_profile}' conflicts with "
                f"this route, which requires '{expected}'."
            ),
        )
    return request.model_copy(update={"execution_profile": expected})


def _execute_v2(
    request: EnergyChatV2Request,
    execution_profile: ExecutionProfile,
    http_request: Request,
) -> EnergyChatV2Response:
    try:
        _require_v2_enabled()
        if request.thread_id is not None:
            claim_resource(http_request, "thread", request.thread_id)
        response = _application_runtime(http_request).execute(
            _bind_route_profile(request, execution_profile),
            execution_profile,
        )
        claim_resource(http_request, "thread", response.thread_id)
        return response
    except HTTPException:
        raise
    except ThreadCheckpointConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail=build_v2_error_detail(
                "thread_checkpoint_conflict",
                str(exc),
                request_id=request.request_id,
                trace_id=request.trace_id,
            ).model_dump(),
        ) from exc
    except ProviderUnavailableError as exc:
        raise HTTPException(
            status_code=400,
            detail=build_v2_error_detail(
                "provider_unavailable",
                exc.detail,
                request_id=request.request_id,
                trace_id=request.trace_id,
            ).model_dump(),
        ) from exc
    except UnsupportedProfileError as exc:
        raise HTTPException(
            status_code=400,
            detail=build_v2_error_detail(
                f"unsupported_{exc.field}",
                exc.detail,
                request_id=request.request_id,
                trace_id=request.trace_id,
            ).model_dump(),
        ) from exc
    except ProviderBudgetExceededError as exc:
        raise HTTPException(
            status_code=400,
            detail=build_v2_error_detail(
                "provider_budget_exceeded",
                str(exc),
                request_id=request.request_id,
                trace_id=request.trace_id,
            ).model_dump(),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=build_v2_error_detail(
                "internal_error",
                "Graph execution failed. See server logs for details.",
                request_id=request.request_id,
                trace_id=request.trace_id,
            ).model_dump(),
        ) from exc


def _execute_v2_monitored(
    request: EnergyChatV2Request,
    execution_profile: ExecutionProfile,
    http_request: Request,
) -> EnergyChatV2Response:
    started = perf_counter()
    try:
        response = _execute_v2(request, execution_profile, http_request)
    except HTTPException:
        _MONITORING.record_error(wall_latency_ms=_elapsed_ms(started))
        raise
    metrics = response.provider_metrics_summary
    _MONITORING.record_success(
        wall_latency_ms=_elapsed_ms(started),
        provider_call_count=metrics.provider_call_count,
        provider_cost_usd=metrics.total_cost_usd,
        disposition=response.final_disposition,
    )
    return response


def _elapsed_ms(started: float) -> int:
    return max(0, round((perf_counter() - started) * 1000))


@router.post("/v2/chat", response_model=EnergyChatV2Response)
def chat_v2_deterministic(
    request: EnergyChatV2Request,
    http_request: Request,
) -> EnergyChatV2Response:
    return _execute_v2_monitored(request, "deterministic", http_request)


@router.post("/v2/chat/live", response_model=EnergyChatV2Response)
def chat_v2_live(
    request: EnergyChatV2Request,
    http_request: Request,
) -> EnergyChatV2Response:
    return _execute_v2_monitored(request, "live_bounded", http_request)


@router.get("/v2/monitoring", response_model=MonitoringSnapshot)
def monitoring_snapshot() -> MonitoringSnapshot:
    return _MONITORING.snapshot()


@router.get("/v2/monitoring/dashboard", response_class=HTMLResponse, include_in_schema=False)
def monitoring_dashboard() -> HTMLResponse:
    return HTMLResponse(render_monitoring_dashboard(_MONITORING.snapshot()))


@router.get(
    "/v2/threads/{thread_id}/state",
    response_model=EnergyChatV2ThreadStateResponse,
)
def get_v2_thread_state(
    http_request: Request,
    thread_id: str = Path(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_-]+$"),
) -> EnergyChatV2ThreadStateResponse:
    _require_v2_enabled()
    assert_resource_owner(http_request, "thread", thread_id)
    try:
        return _application_runtime(http_request).get_thread_state(thread_id)
    except ThreadCheckpointNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=build_v2_error_detail(
                "thread_checkpoint_not_found",
                "No checkpoint exists for this thread.",
            ).model_dump(),
        ) from exc


@router.post(
    "/v2/threads/{thread_id}/replay",
    response_model=EnergyChatV2Response,
)
def replay_v2_thread(
    http_request: Request,
    thread_id: str = Path(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_-]+$"),
) -> EnergyChatV2Response:
    _require_v2_enabled()
    assert_resource_owner(http_request, "thread", thread_id)
    try:
        return _application_runtime(http_request).replay(thread_id)
    except ThreadCheckpointNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=build_v2_error_detail(
                "thread_checkpoint_not_found",
                "No checkpoint exists for this thread.",
            ).model_dump(),
        ) from exc
