"""Typed HTTP transport for process-local human interrupt and resume."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Request

from app.energy_chat.api_v2_contracts import (
    EnergyChatV2HumanResumeRequest,
    EnergyChatV2Request,
    EnergyChatV2Response,
    UnsupportedProfileError,
)
from app.energy_chat.graph_application import build_v2_error_detail
from app.energy_chat.human_gate import (
    HumanActionMismatchError,
    StaleHumanActionError,
)
from app.energy_chat.runtime_container import (
    EnergyChatApplicationRuntime,
    HumanActionAlreadyResumedError,
    ThreadCheckpointConflictError,
    ThreadCheckpointNotFoundError,
)
from app.energy_chat.settings import energy_chat_v2_enabled

router = APIRouter()


def _require_v2_enabled() -> None:
    if not energy_chat_v2_enabled():
        raise HTTPException(
            status_code=404,
            detail={
                "error": "v2_disabled",
                "detail": "Energy Chat V2 is disabled by EACHAT_V2_ENABLED.",
            },
        )


def _runtime(request: Request) -> EnergyChatApplicationRuntime:
    runtime = getattr(request.app.state, "energy_chat_runtime", None)
    if not isinstance(runtime, EnergyChatApplicationRuntime):
        raise RuntimeError("Energy Chat application runtime is not configured")
    return runtime


def _bind_human_route(request: EnergyChatV2Request) -> EnergyChatV2Request:
    if request.execution_profile not in (None, "deterministic"):
        raise UnsupportedProfileError(
            field="execution_profile",
            value=request.execution_profile,
            detail="The human route is deterministic and does not call a live provider.",
        )
    if request.context_profile != "balanced":
        raise UnsupportedProfileError(
            field="context_profile",
            value=request.context_profile,
            detail="Only the balanced context profile is active for human gates.",
        )
    if request.orchestration_mode != "critic":
        raise UnsupportedProfileError(
            field="orchestration_mode",
            value=request.orchestration_mode,
            detail="Only critic orchestration is active for human gates.",
        )
    if request.allow_provider_fallback:
        raise UnsupportedProfileError(
            field="allow_provider_fallback",
            value="true",
            detail="Provider fallback is not valid on the deterministic human route.",
        )
    return request.model_copy(
        update={"execution_profile": "deterministic", "human_gate": True}
    )


def _profile_error(exc: UnsupportedProfileError, request: EnergyChatV2Request) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail=build_v2_error_detail(
            f"unsupported_{exc.field}",
            exc.detail,
            request_id=request.request_id,
            trace_id=request.trace_id,
        ).model_dump(),
    )


@router.post("/v2/chat/human", response_model=EnergyChatV2Response)
def start_human_gated_chat(
    request: EnergyChatV2Request,
    http_request: Request,
) -> EnergyChatV2Response:
    """Run one deterministic graph and return a typed interrupt when required."""

    _require_v2_enabled()
    try:
        return _runtime(http_request).execute_human(_bind_human_route(request))
    except UnsupportedProfileError as exc:
        raise _profile_error(exc, request) from exc
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
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=build_v2_error_detail(
                "internal_error",
                "Human-gated graph execution failed. See server logs for details.",
                request_id=request.request_id,
                trace_id=request.trace_id,
            ).model_dump(),
        ) from exc


@router.post(
    "/v2/threads/{thread_id}/resume",
    response_model=EnergyChatV2Response,
)
def resume_human_gated_chat(
    submission: EnergyChatV2HumanResumeRequest,
    http_request: Request,
    thread_id: str = Path(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_-]+$"),
) -> EnergyChatV2Response:
    """Validate and resume one process-local pending human interrupt."""

    _require_v2_enabled()
    try:
        return _runtime(http_request).resume_human(thread_id, submission)
    except ThreadCheckpointNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=build_v2_error_detail(
                "thread_checkpoint_not_found",
                "No pending human-gated checkpoint exists for this thread.",
            ).model_dump(),
        ) from exc
    except StaleHumanActionError as exc:
        raise HTTPException(
            status_code=409,
            detail=build_v2_error_detail(
                "stale_human_action",
                str(exc),
            ).model_dump(),
        ) from exc
    except HumanActionMismatchError as exc:
        raise HTTPException(
            status_code=409,
            detail=build_v2_error_detail(
                "human_action_mismatch",
                str(exc),
            ).model_dump(),
        ) from exc
    except HumanActionAlreadyResumedError as exc:
        raise HTTPException(
            status_code=409,
            detail=build_v2_error_detail(
                "human_action_already_resumed",
                "The pending human action has already been applied.",
            ).model_dump(),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=build_v2_error_detail(
                "internal_error",
                "Human-gated graph resume failed. See server logs for details.",
            ).model_dump(),
        ) from exc
