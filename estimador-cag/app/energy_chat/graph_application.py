"""Application service: V2 request → graph → authoritative V2 response."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from app.energy_chat.api_v2_contracts import (
    EnergyChatV2ErrorDetail,
    EnergyChatV2Request,
    EnergyChatV2Response,
    ExecutionProfile,
    IDFactory,
    ProviderMetricsSummary,
    ProviderUnavailableError,
    UnsupportedProfileError,
    UUID4IDFactory,
)
from app.energy_chat.candidate_provider import (
    CandidateProvider,
    DeterministicCandidateProvider,
    ProviderBudget,
)
from app.energy_chat.committee_orchestration import (
    CommitteeCandidateProvider,
    resolve_adaptive_orchestration,
)
from app.energy_chat.graph_checkpoint import InMemoryCheckpointer
from app.energy_chat.graph_runtime import run_energy_chat_graph
from app.energy_chat.graph_state import EnergyChatGraphState
from app.energy_chat.human_gate import HumanGateMode
from app.energy_chat.observability import compute_graph_execution_metrics
from app.energy_chat.provider_adapters import build_catalog_candidate_provider
from app.energy_chat.provider_catalog import resolve_effort_profile


def _no_legacy_live_provider() -> CandidateProvider | None:
    """Compatibility injection seam for historical fake-provider tests only."""

    return None


BaselineCandidateProvider: Callable[[], CandidateProvider | None] = (
    _no_legacy_live_provider
)


def run_graph_chat_v2(
    request: EnergyChatV2Request,
    *,
    execution_profile: ExecutionProfile | None = None,
    provider: CandidateProvider | None = None,
    id_factory: IDFactory | None = None,
    checkpointer: object | None = None,
    human_gate_mode: HumanGateMode = "disabled",
) -> EnergyChatV2Response:
    active_id_factory = id_factory or UUID4IDFactory()
    active_execution_profile = _resolve_execution_profile(
        request, route_profile=execution_profile
    )
    _validate_v2_selectors(request, active_execution_profile)
    resolved_orchestration, orchestration_reason = _resolve_orchestration(
        request, active_execution_profile
    )
    thread_id = request.thread_id or active_id_factory.new_thread_id()
    request_id = request.request_id or active_id_factory.new_request_id()
    trace_id = request.trace_id or active_id_factory.new_trace_id()
    materialized_request = request.model_copy(
        update={
            "thread_id": thread_id,
            "request_id": request_id,
            "trace_id": trace_id,
            "execution_profile": active_execution_profile,
            "metadata": {
                **request.metadata,
                "resolved_orchestration_mode": resolved_orchestration,
                "orchestration_reason": orchestration_reason,
            },
        }
    )
    resolved_provider = provider or _resolve_provider(
        materialized_request, active_execution_profile
    )
    budget = _resolve_budget(materialized_request)
    active_checkpointer = checkpointer
    if active_checkpointer is None and active_execution_profile == "deterministic":
        active_checkpointer = InMemoryCheckpointer()
    saver = (
        getattr(active_checkpointer, "langgraph_saver", None)
        if active_checkpointer is not None
        else None
    )
    state = EnergyChatGraphState(
        thread_id=thread_id,
        request_id=request_id,
        trace_id=trace_id,
        user_request=materialized_request.user_message,
        mode=materialized_request.mode,
        policy_version="unresolved",
        constraints=materialized_request.required_constraints,
    )
    result = run_energy_chat_graph(
        state,
        provider=resolved_provider,
        budget=budget,
        checkpointer=saver,
        human_gate_mode=human_gate_mode,
    )
    checkpoint_id = (
        active_checkpointer.get_checkpoint_id(thread_id)
        if active_checkpointer is not None
        else None
    )
    return project_v2_response(
        result,
        materialized_request,
        active_execution_profile,
        checkpoint_id=checkpoint_id,
        restart_persistent=bool(
            getattr(active_checkpointer, "restart_persistent", False)
        ),
    )


def _resolve_execution_profile(
    request: EnergyChatV2Request,
    *,
    route_profile: ExecutionProfile | None,
) -> ExecutionProfile:
    active = route_profile or request.execution_profile or "deterministic"
    if (
        route_profile is not None
        and request.execution_profile is not None
        and request.execution_profile != route_profile
    ):
        raise UnsupportedProfileError(
            field="execution_profile",
            value=request.execution_profile,
            detail=(
                f"Execution profile '{request.execution_profile}' conflicts with "
                f"the selected route, which requires '{route_profile}'."
            ),
        )
    return active


def _validate_v2_selectors(
    request: EnergyChatV2Request,
    execution_profile: ExecutionProfile,
) -> None:
    if request.context_profile != "balanced":
        raise UnsupportedProfileError(
            field="context_profile",
            value=request.context_profile,
            detail=(
                f"Context profile '{request.context_profile}' is not implemented; "
                "only 'balanced' is active"
            ),
        )
    if request.orchestration_mode == "single":
        raise UnsupportedProfileError(
            field="orchestration_mode",
            value=request.orchestration_mode,
            detail="Single mode is not a distinct runtime; use critic.",
        )
    if execution_profile == "live_bounded" and request.orchestration_mode != "critic":
        raise UnsupportedProfileError(
            field="orchestration_mode",
            value=request.orchestration_mode,
            detail=(
                "Live committee/adaptive orchestration is blocked until matched "
                "quality, cost, and latency calibration exists."
            ),
        )
    if request.human_gate:
        raise UnsupportedProfileError(
            field="human_gate",
            value="true",
            detail="Use the dedicated typed human-gate route.",
        )
    if execution_profile == "deterministic" and request.allow_provider_fallback:
        raise UnsupportedProfileError(
            field="allow_provider_fallback",
            value="true",
            detail="Provider fallback is not valid on the deterministic route",
        )


def _resolve_orchestration(
    request: EnergyChatV2Request,
    execution_profile: ExecutionProfile,
) -> tuple[str, str]:
    if execution_profile == "live_bounded":
        return "critic", "live route uses calibrated critic orchestration only"
    if request.orchestration_mode == "committee":
        return (
            "committee",
            "caller selected bounded three-proposal deterministic committee",
        )
    if request.orchestration_mode == "adaptive":
        decision = resolve_adaptive_orchestration(
            user_request=request.user_message,
            mode=request.mode,
            constraints=request.required_constraints,
            required_sections=request.required_sections,
        )
        return (
            decision.resolved_mode,
            "adaptive policy: " + ",".join(decision.reason_codes),
        )
    return "critic", "caller selected the standard critic pipeline"


def _resolve_provider(
    request: EnergyChatV2Request,
    execution_profile: ExecutionProfile,
) -> CandidateProvider:
    if execution_profile == "deterministic":
        if request.metadata.get("resolved_orchestration_mode") == "committee":
            return CommitteeCandidateProvider()
        return DeterministicCandidateProvider()
    if request.provider_preference == "auto":
        raise ProviderUnavailableError(
            provider="auto",
            detail=(
                "Automatic provider routing is not calibrated. "
                "Select a verified provider explicitly."
            ),
        )
    resolved = resolve_effort_profile(
        request.provider_preference, request.effort_profile
    )
    if resolved is None:
        raise ProviderUnavailableError(
            provider=request.provider_preference,
            detail=(
                f"Provider '{request.provider_preference}' with effort "
                f"'{request.effort_profile}' has no verified compatible model."
            ),
        )
    if request.allow_provider_fallback:
        raise ProviderUnavailableError(
            provider=request.provider_preference,
            detail=(
                "Cross-provider fallback is not implemented on the isolated V2 "
                "production adapter. Retry with fallback disabled and select the "
                "verified provider explicitly."
            ),
        )
    if request.provider_preference == "deepseek":
        injected = BaselineCandidateProvider()
        if injected is not None:
            return injected
    try:
        return build_catalog_candidate_provider(
            request.provider_preference,
            request.effort_profile,
        )
    except (ValueError, RuntimeError) as exc:
        raise ProviderUnavailableError(
            provider=request.provider_preference,
            detail=(
                f"Provider '{request.provider_preference}' is catalogued but its live "
                "adapter is unavailable with the current credential/configuration."
            ),
        ) from exc


def _resolve_budget(request: EnergyChatV2Request) -> ProviderBudget:
    if request.effort_profile == "fast":
        return ProviderBudget(
            max_output_tokens=400,
            max_cost_usd=0.01,
            max_latency_ms=5_000,
        )
    if request.effort_profile == "max":
        return ProviderBudget(
            max_output_tokens=4_000,
            max_cost_usd=0.10,
            max_latency_ms=60_000,
        )
    return ProviderBudget()


def project_v2_response(
    result: EnergyChatGraphState,
    request: EnergyChatV2Request,
    execution_profile: ExecutionProfile,
    *,
    checkpoint_id: str | None = None,
    replayed_from_checkpoint: bool = False,
    restart_persistent: bool = False,
) -> EnergyChatV2Response:
    metrics_list = result.provider_metrics
    resolved_orchestration = request.metadata.get(
        "resolved_orchestration_mode", "critic"
    )
    orchestration_reason = request.metadata.get(
        "orchestration_reason", "standard critic pipeline"
    )
    orchestration_candidate_count = (
        3 if resolved_orchestration == "committee" else 1
    )
    if not metrics_list:
        served_provider = "none"
        served_model = None
        fallback_used = False
        routing_reason = "generation skipped pending evidence; no provider call was made"
    else:
        last = metrics_list[-1]
        served_provider = last.provider
        served_model = last.model
        fallback_used = any(item.fallback_used for item in metrics_list)
        if replayed_from_checkpoint:
            routing_reason = "response replayed from the authoritative checkpoint"
        elif execution_profile == "deterministic":
            routing_reason = (
                f"{orchestration_reason}; deterministic provider={last.provider}"
            )
        elif fallback_used:
            routing_reason = (
                f"authorized fallback served {last.provider}/{last.model}; "
                f"allowlist={request.fallback_provider_allowlist}"
            )
        else:
            routing_reason = (
                f"live route served {last.provider}/{last.model} without fallback"
            )
    provider_summary = ProviderMetricsSummary(
        provider_call_count=len(metrics_list),
        providers_used=list(dict.fromkeys(item.provider for item in metrics_list)),
        models_used=list(dict.fromkeys(item.model for item in metrics_list)),
        total_input_tokens=_sum_or_none(item.input_tokens for item in metrics_list),
        total_output_tokens=_sum_or_none(item.output_tokens for item in metrics_list),
        total_cost_usd=sum(item.cost_usd for item in metrics_list),
        total_latency_ms=sum(item.latency_ms for item in metrics_list),
        fallback_used=fallback_used,
        fallback_authorized=request.allow_provider_fallback,
        fallback_provider_allowlist=list(request.fallback_provider_allowlist),
    )
    graph_metrics = compute_graph_execution_metrics(
        thread_id=result.thread_id,
        request_id=result.request_id,
        trace_id=result.trace_id,
        graph_status=result.status,
        provider_metrics=result.provider_metrics,
        trace_events=result.trace_events,
        errors=result.errors,
        node_spans=result.node_spans,
    )
    final_disposition = (
        result.decision_outcomes[-1].disposition
        if result.decision_outcomes
        else None
    )
    execution_markers = (
        result.final_projection.execution_markers
        if result.final_projection
        else ["no_external_provider_call", "no_tool_execution"]
    )
    limitations = list(
        dict.fromkeys(
            limitation
            for entry in result.decision_ledger_entries
            for limitation in entry.limitations
        )
    )
    if not result.decision_ledger_entries and result.status == "awaiting_evidence":
        limitations.append("External evidence is required before candidate generation.")
    if replayed_from_checkpoint:
        limitations.append(
            "Replay was loaded from durable storage."
            if restart_persistent
            else "Replay is process-local; application restart loses in-memory checkpoints."
        )
    return EnergyChatV2Response(
        thread_id=result.thread_id,
        request_id=result.request_id,
        trace_id=result.trace_id,
        graph_status=result.status,
        awaiting_evidence=result.status == "awaiting_evidence",
        source_need=result.source_need,
        evidence_refs=result.evidence_refs,
        evidence_body_metadata=result.evidence_body_metadata,
        citation_validations=result.citation_validations,
        final_disposition=final_disposition,
        final_answer=result.final_answer,
        energy_card_v2=result.energy_card_v2,
        execution_markers=execution_markers,
        graph_metrics=graph_metrics,
        candidate_count=len(result.candidate_versions),
        repair_count=len(result.repair_requests),
        repair_outcomes=[item.outcome for item in result.repair_results],
        requested_provider=request.provider_preference,
        served_provider=served_provider,
        served_model=served_model,
        fallback_used=fallback_used,
        fallback_authorized=request.allow_provider_fallback,
        fallback_provider_allowlist=list(request.fallback_provider_allowlist),
        routing_reason=routing_reason,
        requested_orchestration_mode=request.orchestration_mode,
        resolved_orchestration_mode=resolved_orchestration,
        orchestration_candidate_count=orchestration_candidate_count,
        orchestration_reason=orchestration_reason,
        provider_metrics_summary=provider_summary,
        ledger_entry_ids=[
            item.ledger_entry_id for item in result.decision_ledger_entries
        ],
        trace_summary=graph_metrics.safe_trace_summary,
        limitations=list(dict.fromkeys(limitations)),
        checkpoint_id=checkpoint_id,
        replayed_from_checkpoint=replayed_from_checkpoint,
    )


def build_v2_error_detail(
    error: str,
    detail: str,
    *,
    request_id: str | None = None,
    trace_id: str | None = None,
) -> EnergyChatV2ErrorDetail:
    return EnergyChatV2ErrorDetail(
        error=error,
        detail=detail,
        request_id=request_id,
        trace_id=trace_id,
    )


def _sum_or_none(values: Iterable[int | None]) -> int | None:
    present = [int(value) for value in values if value is not None]
    return sum(present) if present else None
