"""Revision-guarded multi-turn conversation routes for EACHAT V2."""

from __future__ import annotations

from time import perf_counter

from fastapi import APIRouter, HTTPException, Request, Response

from app.energy_chat.api_v2_contracts import (
    ProviderUnavailableError,
    UnsupportedProfileError,
)
from app.energy_chat.candidate_provider import ProviderBudgetExceededError
from app.energy_chat.conversation_models import (
    ConversationCreateResponse,
    ConversationDeleteResponse,
    ConversationHistoryResponse,
    ConversationTurnRequest,
    ConversationTurnResponse,
)
from app.energy_chat.conversation_service import (
    create_conversation,
    execute_conversation_turn,
    get_conversation_history,
)
from app.energy_chat.conversation_store import (
    ConversationAlreadyExistsError,
    ConversationNotFoundError,
    ConversationRevisionConflictError,
    ConversationStore,
    ConversationTurnConflictError,
)
from app.energy_chat.graph_application import build_v2_error_detail
from app.energy_chat.monitoring import get_monitoring_window
from app.energy_chat.ownership_http import (
    assert_resource_owner,
    claim_resource,
    delete_resource_owner,
)
from app.energy_chat.runtime_container import EnergyChatApplicationRuntime
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


def _store(request: Request) -> ConversationStore:
    store = getattr(request.app.state, "energy_chat_conversation_store", None)
    if store is None:
        raise RuntimeError("Energy Chat conversation storage is not configured")
    return store


def _runtime(request: Request) -> EnergyChatApplicationRuntime:
    runtime = getattr(request.app.state, "energy_chat_runtime", None)
    if not isinstance(runtime, EnergyChatApplicationRuntime):
        raise RuntimeError("Energy Chat application runtime is not configured")
    return runtime


@router.post(
    "/v2/conversations",
    response_model=ConversationCreateResponse,
    status_code=201,
)
def create_v2_conversation(http_request: Request) -> ConversationCreateResponse:
    _require_v2_enabled()
    response = create_conversation(_store(http_request))
    try:
        claim_resource(http_request, "conversation", response.conversation_id)
    except HTTPException:
        _store(http_request).delete(response.conversation_id)
        raise
    return response


@router.get(
    "/v2/conversations/{conversation_id}",
    response_model=ConversationHistoryResponse,
)
def get_v2_conversation(
    conversation_id: str,
    http_request: Request,
) -> ConversationHistoryResponse:
    _require_v2_enabled()
    assert_resource_owner(http_request, "conversation", conversation_id)
    try:
        return get_conversation_history(_store(http_request), conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "conversation_not_found", "detail": conversation_id},
        ) from exc


@router.delete(
    "/v2/conversations/{conversation_id}",
    response_model=ConversationDeleteResponse,
)
def delete_v2_conversation(
    conversation_id: str,
    http_request: Request,
) -> ConversationDeleteResponse:
    _require_v2_enabled()
    assert_resource_owner(http_request, "conversation", conversation_id)
    try:
        _store(http_request).delete(conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "conversation_not_found", "detail": conversation_id},
        ) from exc
    delete_resource_owner(http_request, "conversation", conversation_id)
    return ConversationDeleteResponse(conversation_id=conversation_id)


@router.post(
    "/v2/conversations/{conversation_id}/turns",
    response_model=ConversationTurnResponse,
)
def create_v2_conversation_turn(
    conversation_id: str,
    request: ConversationTurnRequest,
    http_request: Request,
    response: Response,
) -> ConversationTurnResponse:
    started = perf_counter()
    completed = False
    _require_v2_enabled()
    assert_resource_owner(http_request, "conversation", conversation_id)
    try:
        result = execute_conversation_turn(
            store=_store(http_request),
            runtime=_runtime(http_request),
            conversation_id=conversation_id,
            request=request,
        )
        claim_resource(http_request, "thread", result.turn.graph_thread_id)
        if result.replayed_idempotency_key:
            response.headers["X-Idempotent-Replay"] = "true"
        graph_response = result.turn.graph_response
        metrics = graph_response.provider_metrics_summary
        _MONITORING.record_success(
            wall_latency_ms=_elapsed_ms(started),
            provider_call_count=metrics.provider_call_count,
            provider_cost_usd=metrics.total_cost_usd,
            disposition=graph_response.final_disposition,
        )
        completed = True
        return result
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "conversation_not_found", "detail": conversation_id},
        ) from exc
    except ConversationRevisionConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": "conversation_revision_conflict", "detail": str(exc)},
        ) from exc
    except (ConversationTurnConflictError, ConversationAlreadyExistsError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": "conversation_turn_conflict", "detail": str(exc)},
        ) from exc
    except ProviderUnavailableError as exc:
        raise HTTPException(
            status_code=400,
            detail=build_v2_error_detail(
                "provider_unavailable",
                exc.detail,
            ).model_dump(),
        ) from exc
    except UnsupportedProfileError as exc:
        raise HTTPException(
            status_code=400,
            detail=build_v2_error_detail(
                f"unsupported_{exc.field}",
                exc.detail,
            ).model_dump(),
        ) from exc
    except ProviderBudgetExceededError as exc:
        raise HTTPException(
            status_code=400,
            detail=build_v2_error_detail(
                "provider_budget_exceeded",
                str(exc),
            ).model_dump(),
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=build_v2_error_detail(
                "internal_error",
                "Conversation turn execution failed. See server logs for details.",
            ).model_dump(),
        ) from exc
    finally:
        if not completed:
            _MONITORING.record_error(wall_latency_ms=_elapsed_ms(started))


def _elapsed_ms(started: float) -> int:
    return max(0, round((perf_counter() - started) * 1000))
