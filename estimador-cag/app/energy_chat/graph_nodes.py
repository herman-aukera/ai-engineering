"""Provider-free interpretation and policy nodes for Energy Aware Chat.

The functions in this module return explicit state deltas. They do not depend on
LangGraph, mutate input state, call providers, or make authoritative decisions.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import Field

from app.energy_chat.contracts import Mode, RequestPolicyAssessment
from app.energy_chat.graph_state import (
    EnergyChatGraphState,
    GraphStateRecord,
    TraceEvent,
    append_unique_records,
    build_trace_event,
    validated_state_update,
)
from app.energy_chat.policies import assess_request_policy, default_chat_lite_policy


class InterpretationDelta(GraphStateRecord):
    """Fields owned by the deterministic request interpretation node."""

    user_request: str = Field(min_length=1)
    mode: Mode
    status: Literal["interpreted"] = "interpreted"
    trace_events: list[TraceEvent] = Field(min_length=1, max_length=1)


class PolicyConstraintsDelta(GraphStateRecord):
    """Fields owned by the deterministic policy and constraint loading node."""

    policy_version: str = Field(min_length=1)
    request_policy: RequestPolicyAssessment
    constraints: list[str]
    status: Literal["policy_ready"] = "policy_ready"
    trace_events: list[TraceEvent] = Field(min_length=1, max_length=1)


def interpret_request(state: EnergyChatGraphState) -> InterpretationDelta:
    """Normalize request text while preserving the caller's explicit supported mode."""

    normalized_request = _normalize_space(state.user_request)
    event = build_trace_event(
        state,
        event_type="request_interpreted",
        producer="interpret_request",
        payload={
            "mode": state.mode,
            "normalized_request_chars": len(normalized_request),
        },
    )
    return InterpretationDelta(
        user_request=normalized_request,
        mode=state.mode,
        trace_events=[event],
    )


def load_policy_and_constraints(state: EnergyChatGraphState) -> PolicyConstraintsDelta:
    """Load the existing deterministic policy and normalize explicit constraints."""

    policy = default_chat_lite_policy()
    request_policy = assess_request_policy(state.user_request)
    constraints = _normalize_constraints(state.constraints)
    event = build_trace_event(
        state,
        event_type="policy_and_constraints_loaded",
        producer="load_policy_and_constraints",
        payload={
            "constraint_count": len(constraints),
            "policy_id": policy.policy_id,
            "policy_version": policy.version,
            "request_policy_directive": request_policy.directive,
            "request_policy_rule_id": request_policy.rule_id,
            "request_policy_version": request_policy.version,
        },
    )
    return PolicyConstraintsDelta(
        policy_version=policy.version,
        request_policy=request_policy,
        constraints=constraints,
        trace_events=[event],
    )


def apply_interpretation_delta(
    state: EnergyChatGraphState, delta: InterpretationDelta
) -> EnergyChatGraphState:
    """Apply interpretation-owned replacements and the append-only trace reducer."""

    return validated_state_update(
        state,
        user_request=delta.user_request,
        mode=delta.mode,
        status=delta.status,
        trace_events=append_unique_records(
            state.trace_events, delta.trace_events, id_field="event_id"
        ),
    )


def apply_policy_delta(
    state: EnergyChatGraphState, delta: PolicyConstraintsDelta
) -> EnergyChatGraphState:
    """Apply policy-owned replacements and the append-only trace reducer."""

    return validated_state_update(
        state,
        policy_version=delta.policy_version,
        request_policy=delta.request_policy,
        constraints=delta.constraints,
        status=delta.status,
        trace_events=append_unique_records(
            state.trace_events, delta.trace_events, id_field="event_id"
        ),
    )


def _normalize_constraints(constraints: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for constraint in constraints:
        value = _normalize_space(constraint)
        if not value or value.casefold() in seen:
            continue
        seen.add(value.casefold())
        normalized.append(value)
    return normalized


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
