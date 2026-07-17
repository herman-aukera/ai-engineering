"""Replay-safe candidate generation node for Energy Aware Chat."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.energy_chat.candidate_provider import (
    CandidateGenerationResult,
    CandidateProvider,
    CandidateProviderRequest,
    ProviderBudget,
    enforce_provider_budget,
)
from app.energy_chat.graph_state import (
    CandidateVersion,
    EnergyChatGraphState,
    GraphStateRecord,
    ProviderMetrics,
    TraceEvent,
    append_unique_records,
    append_unique_values,
    build_trace_event,
    validated_state_update,
)


class CandidateDelta(GraphStateRecord):
    """Fields owned by the candidate generation node."""

    candidate_versions: list[CandidateVersion] = Field(min_length=1, max_length=1)
    active_candidate_id: str = Field(min_length=1)
    provider_metrics: list[ProviderMetrics] = Field(min_length=1, max_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    status: Literal["candidate_ready"] = "candidate_ready"
    trace_events: list[TraceEvent] = Field(min_length=1, max_length=1)


def generate_candidate(
    state: EnergyChatGraphState,
    *,
    provider: CandidateProvider,
    budget: ProviderBudget | None = None,
    version: int = 1,
) -> CandidateDelta:
    """Generate one candidate or replay its retained result without another call."""

    active_budget = budget or ProviderBudget()
    candidate_id = f"{state.request_id}:candidate:{version}"
    provider_call_id = f"{candidate_id}:provider-call"
    retained = next(
        (candidate for candidate in state.candidate_versions if candidate.candidate_id == candidate_id),
        None,
    )
    if retained is not None:
        metrics = next(
            (
                item
                for item in state.provider_metrics
                if item.provider_call_id == provider_call_id
            ),
            None,
        )
        if metrics is None:
            raise ValueError("Retained candidate is missing its provider metrics")
        result = CandidateGenerationResult(
            answer=retained.answer,
            evidence_refs=retained.evidence_refs,
            metrics=metrics,
        )
    else:
        raw_result = provider.generate(
            CandidateProviderRequest(
                provider_call_id=provider_call_id,
                user_request=state.user_request,
                mode=state.mode,
                constraints=state.constraints,
                evidence_refs=state.evidence_refs,
                project_rag=state.project_rag,
                max_tokens=active_budget.max_output_tokens,
            )
        )
        result = CandidateGenerationResult.model_validate(raw_result)
        if result.metrics.provider_call_id != provider_call_id:
            raise ValueError("Candidate provider returned mismatched provider_call_id")
        enforce_provider_budget(result.metrics, active_budget)
        retained = CandidateVersion(
            candidate_id=candidate_id,
            version=version,
            answer=result.answer,
            producer="generate_candidate",
            evidence_refs=append_unique_values(state.evidence_refs, result.evidence_refs),
            provider_call_id=provider_call_id,
        )

    event = build_trace_event(
        state,
        event_type="candidate_generated",
        event_key=f"candidate_generated:{candidate_id}",
        producer="generate_candidate",
        payload={
            "candidate_id": candidate_id,
            "fallback_used": result.metrics.fallback_used,
            "provider": result.metrics.provider,
            "provider_call_id": provider_call_id,
        },
    )
    return CandidateDelta(
        candidate_versions=[retained],
        active_candidate_id=candidate_id,
        provider_metrics=[result.metrics],
        evidence_refs=retained.evidence_refs,
        trace_events=[event],
    )


def apply_candidate_delta(
    state: EnergyChatGraphState, delta: CandidateDelta
) -> EnergyChatGraphState:
    """Apply candidate history, metrics, evidence, and singular active candidate."""

    return validated_state_update(
        state,
        candidate_versions=append_unique_records(
            state.candidate_versions, delta.candidate_versions, id_field="candidate_id"
        ),
        active_candidate_id=delta.active_candidate_id,
        provider_metrics=append_unique_records(
            state.provider_metrics, delta.provider_metrics, id_field="provider_call_id"
        ),
        evidence_refs=append_unique_values(state.evidence_refs, delta.evidence_refs),
        status=delta.status,
        trace_events=append_unique_records(
            state.trace_events, delta.trace_events, id_field="event_id"
        ),
    )
