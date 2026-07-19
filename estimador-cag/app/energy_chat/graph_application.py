"""Application service: V2 request → graph → authoritative V2 response.

Each V2 request invokes exactly one graph execution. No legacy fallback.
Response authority comes from graph state and Decision Ledger.
"""

from __future__ import annotations

from app.energy_chat.api_v2_contracts import (
    EnergyChatV2Request,
    EnergyChatV2Response,
    EnergyChatV2ErrorDetail,
    IDFactory,
    UUID4IDFactory,
    ProviderMetricsSummary,
    ProviderUnavailableError,
    UnsupportedProfileError,
)
from app.energy_chat.candidate_provider import (
    BaselineCandidateProvider,
    CandidateProvider,
    DeterministicCandidateProvider,
    ProviderBudget,
    ProviderBudgetExceededError,
)
from app.energy_chat.graph_runtime import run_energy_chat_graph
from app.energy_chat.graph_state import EnergyChatGraphState


def run_graph_chat_v2(
    request: EnergyChatV2Request,
    *,
    provider: CandidateProvider | None = None,
    id_factory: IDFactory | None = None,
) -> EnergyChatV2Response:
    """One V2 request → exactly one graph execution → authoritative V2 response."""

    active_id_factory = id_factory or UUID4IDFactory()

    # 1. Validate selector contracts (fail closed on unsupported profiles)
    _validate_v2_selectors(request)

    # 2. Resolve identity
    thread_id = request.thread_id or active_id_factory.new_thread_id()
    request_id = request.request_id or active_id_factory.new_request_id()
    trace_id = request.trace_id or active_id_factory.new_trace_id()

    # 3. Select provider and budget
    resolved_provider = provider or _resolve_provider(request)
    budget = _resolve_budget(request)

    # 4. Build initial graph state
    state = EnergyChatGraphState(
        thread_id=thread_id,
        request_id=request_id,
        trace_id=trace_id,
        user_request=request.user_message,
        mode=request.mode,
        policy_version="unresolved",
        constraints=request.required_constraints,
    )

    # 5. Execute graph exactly once
    try:
        result = run_energy_chat_graph(
            state,
            provider=resolved_provider,
            budget=budget,
        )
    except ProviderBudgetExceededError:
        raise
    except Exception:
        raise

    # 6. Project authoritative response
    return _project_v2_response(result, request)


def _validate_v2_selectors(request: EnergyChatV2Request) -> None:
    """Fail explicitly on selector values that are valid enums but not yet implemented."""

    if request.context_profile != "balanced":
        raise UnsupportedProfileError(
            field="context_profile",
            value=request.context_profile,
            detail=f"Context profile '{request.context_profile}' is not implemented; only 'balanced' is active in this milestone",
        )

    if request.orchestration_mode != "critic":
        raise UnsupportedProfileError(
            field="orchestration_mode",
            value=request.orchestration_mode,
            detail=f"Orchestration mode '{request.orchestration_mode}' is not implemented; only 'critic' mode is active in this milestone",
        )

    if request.human_gate:
        raise UnsupportedProfileError(
            field="human_gate",
            value="true",
            detail="Human-in-the-loop is not implemented in this milestone",
        )


def _resolve_provider(request: EnergyChatV2Request) -> CandidateProvider:
    """Select the provider adapter from the explicit execution profile.

    deterministic → always DeterministicCandidateProvider (CI-safe, keyless).
    live_bounded → BaselineCandidateProvider for deepseek/auto; fail closed for kimi/openai.
    """

    if request.execution_profile == "deterministic":
        return DeterministicCandidateProvider()

    # live_bounded
    if request.provider_preference in ("auto", "deepseek"):
        return BaselineCandidateProvider()

    raise ProviderUnavailableError(
        provider=request.provider_preference,
        detail=(
            f"Provider '{request.provider_preference}' requires a credentialed adapter "
            "that is deferred to a later milestone. Available: deepseek (default)."
        ),
    )


def _resolve_budget(request: EnergyChatV2Request) -> ProviderBudget:
    """Map effort profile to concrete provider budget limits."""

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
    # balanced
    return ProviderBudget()


def _project_v2_response(
    result: EnergyChatGraphState,
    request: EnergyChatV2Request,
) -> EnergyChatV2Response:
    """Project authoritative graph state into a safe V2 response.

    Derives every field from graph-owned truth. Never reconstructs from UI strings.
    """

    # Provider selection info
    is_deterministic = request.execution_profile == "deterministic"
    metrics_list = result.provider_metrics

    if is_deterministic or not metrics_list:
        served_provider = "deterministic_local"
        served_model = "energy-chat-template-v1"
        fallback_used = False
        routing_reason = "deterministic profile uses local template provider"
    else:
        last = metrics_list[-1]
        served_provider = last.provider
        served_model = last.model
        fallback_used = any(m.fallback_used for m in metrics_list)
        routing_reason = (
            f"live profile routed to {last.provider}/{last.model}"
            f"{' with fallback' if fallback_used else ''}"
        )

    # Safe metrics summary
    metrics_summary = ProviderMetricsSummary(
        provider_call_count=len(metrics_list),
        providers_used=list(dict.fromkeys(m.provider for m in metrics_list)),
        models_used=list(dict.fromkeys(m.model for m in metrics_list)),
        total_input_tokens=_sum_or_none(m.input_tokens for m in metrics_list),
        total_output_tokens=_sum_or_none(m.output_tokens for m in metrics_list),
        total_cost_usd=sum(m.cost_usd for m in metrics_list),
        total_latency_ms=sum(m.latency_ms for m in metrics_list),
        fallback_used=fallback_used,
    )

    # Final disposition
    final_disposition = None
    if result.decision_outcomes:
        final_disposition = result.decision_outcomes[-1].disposition

    # Energy Card v2 from final projection
    energy_card_v2 = result.energy_card_v2

    # Execution markers
    execution_markers = (
        result.final_projection.execution_markers
        if result.final_projection
        else ["no_external_provider_call", "no_tool_execution"]
    )

    # Repair outcomes
    repair_outcomes = [r.outcome for r in result.repair_results]

    # Limitations from ledger entries
    limitations: list[str] = []
    for entry in result.decision_ledger_entries:
        for limit in entry.limitations:
            if limit not in limitations:
                limitations.append(limit)
    if not result.decision_ledger_entries and result.status == "awaiting_evidence":
        limitations.append("External evidence is required before candidate generation.")

    # Safe trace summary (event types and producers only, no payload bodies)
    trace_summary = [
        {
            "event_type": e.event_type,
            "producer": e.producer,
            "sequence": e.sequence,
        }
        for e in result.trace_events
    ]

    return EnergyChatV2Response(
        thread_id=result.thread_id,
        request_id=result.request_id,
        trace_id=result.trace_id,
        graph_status=result.status,
        awaiting_evidence=result.status == "awaiting_evidence",
        source_need=result.source_need,
        evidence_refs=result.evidence_refs,
        final_disposition=final_disposition,
        final_answer=result.final_answer,
        energy_card_v2=energy_card_v2,
        execution_markers=execution_markers,
        candidate_count=len(result.candidate_versions),
        repair_count=len(result.repair_requests),
        repair_outcomes=repair_outcomes,
        requested_provider=request.provider_preference,
        served_provider=served_provider,
        served_model=served_model,
        fallback_used=fallback_used,
        routing_reason=routing_reason,
        provider_metrics_summary=metrics_summary,
        ledger_entry_ids=[e.ledger_entry_id for e in result.decision_ledger_entries],
        trace_summary=trace_summary,
        limitations=limitations,
    )


def build_v2_error_detail(
    error: str,
    detail: str,
    *,
    request_id: str | None = None,
    trace_id: str | None = None,
) -> EnergyChatV2ErrorDetail:
    """Build a safe error detail without stack traces or secrets."""
    return EnergyChatV2ErrorDetail(
        error=error,
        detail=detail,
        request_id=request_id,
        trace_id=trace_id,
    )


def _sum_or_none(values: object) -> int | None:
    """Sum ints or return None when all values are None."""
    total = 0
    any_present = False
    for v in values:  # type: ignore[assignment]
        if v is not None:
            total += int(v)  # type: ignore[arg-type]
            any_present = True
    return total if any_present else None
