"""Versioned, product-local state contracts for Energy Aware Chat orchestration.

This module defines domain truth only. It deliberately has no LangGraph import so
state invariants, persistence fixtures, and reducer behavior remain independently
testable before a graph runtime is introduced.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.energy_chat.audit_models import (
    DecisionLedgerEntry,
    EnergyCardV2,
    FinalAnswerProjection,
)
from app.energy_chat.contracts import (
    CriticFinding,
    EnergyCard,
    EnergyScore,
    Mode,
    ProjectRagResult,
    RequestPolicyAssessment,
    SourceNeedResult,
)
from app.energy_chat.evidence_hardening import (
    CandidateCitationValidation,
    EvidenceBodyMetadata,
)
from app.energy_chat.human_gate import HumanActionRequest
from app.energy_chat.observability import NodeSpan

GRAPH_STATE_SCHEMA_VERSION = "1.0.0"
GRAPH_STATE_CONTRACT_VERSION = "1.0.0"

GraphStatus = Literal[
    "received",
    "interpreted",
    "policy_ready",
    "evidence_classified",
    "awaiting_evidence",
    "evidence_ready",
    "candidate_ready",
    "criticized",
    "scored",
    "evaluated",
    "repair_requested",
    "awaiting_human",
    "completed",
    "failed",
]
Disposition = Literal["accept", "repair", "clarify", "reject", "refuse", "escalate"]


class GraphStateRecord(BaseModel):
    """Strict base for records that can cross a checkpoint boundary."""

    model_config = ConfigDict(extra="forbid")


class CandidateVersion(GraphStateRecord):
    candidate_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    answer: str
    producer: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    provider_call_id: str | None = None


class EnergyScoreRecord(GraphStateRecord):
    score_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    score: EnergyScore


class CriticPanelRecord(GraphStateRecord):
    panel_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    critic_version: str = Field(min_length=1)
    findings: list[CriticFinding] = Field(default_factory=list)


class DecisionOutcome(GraphStateRecord):
    decision_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    score_id: str = Field(min_length=1)
    disposition: Disposition
    reason: str = Field(min_length=1)
    required_repairs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    policy_rule_id: str = "legacy_energy_decider"


class RepairRequest(GraphStateRecord):
    repair_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    instructions: list[str] = Field(min_length=1)
    source_decision_id: str | None = None
    target_candidate_id: str | None = None
    proposed_answer: str | None = None
    repairs_applied: list[str] = Field(default_factory=list)


class RepairResultRecord(GraphStateRecord):
    result_id: str = Field(min_length=1)
    repair_id: str = Field(min_length=1)
    source_candidate_id: str = Field(min_length=1)
    target_candidate_id: str = Field(min_length=1)
    energy_before: int = Field(ge=0)
    energy_after: int = Field(ge=0)
    outcome: Literal["improved", "no_improvement", "budget_exhausted", "not_repairable"]


class RetryBudget(GraphStateRecord):
    max_attempts: int = Field(default=1, ge=0, le=8)
    attempts_used: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def attempts_cannot_exceed_limit(self) -> RetryBudget:
        if self.attempts_used > self.max_attempts:
            raise ValueError("Repair attempts exceed retry budget")
        return self

    @property
    def remaining(self) -> int:
        return self.max_attempts - self.attempts_used


class CostBudget(GraphStateRecord):
    limit_usd: float = Field(default=0.10, ge=0.0)
    spent_usd: float = Field(default=0.0, ge=0.0)

    @model_validator(mode="after")
    def spend_cannot_exceed_limit(self) -> CostBudget:
        if self.spent_usd > self.limit_usd + 1e-12:
            raise ValueError("Provider spend exceeds cost budget")
        return self

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.limit_usd - self.spent_usd)


class TraceEvent(GraphStateRecord):
    event_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    producer: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class ErrorRecord(GraphStateRecord):
    error_id: str = Field(min_length=1)
    producer: str = Field(min_length=1)
    code: str = Field(min_length=1)
    message: str
    retryable: bool = False


class ProviderMetrics(GraphStateRecord):
    provider_call_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    tier: str = Field(min_length=1)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)
    latency_ms: int = Field(default=0, ge=0)
    retries: int = Field(default=0, ge=0)
    fallback_used: bool = False
    finish_reason: str | None = None


class EnergyChatGraphState(GraphStateRecord):
    """Authoritative v1 state for one Energy Aware Chat request."""

    schema_version: Literal["1.0.0"] = GRAPH_STATE_SCHEMA_VERSION
    contract_version: Literal["1.0.0"] = GRAPH_STATE_CONTRACT_VERSION
    thread_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    user_request: str = Field(min_length=1)
    mode: Mode = "chat_lite"
    policy_version: str = Field(min_length=1)
    request_policy: RequestPolicyAssessment | None = None
    constraints: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    evidence_body_metadata: list[EvidenceBodyMetadata] = Field(default_factory=list)
    citation_validations: list[CandidateCitationValidation] = Field(default_factory=list)
    source_need: SourceNeedResult | None = None
    project_rag: ProjectRagResult | None = None
    candidate_versions: list[CandidateVersion] = Field(default_factory=list)
    active_candidate_id: str | None = None
    provider_metrics: list[ProviderMetrics] = Field(default_factory=list)
    critic_findings: list[CriticFinding] = Field(default_factory=list)
    critic_panels: list[CriticPanelRecord] = Field(default_factory=list)
    energy_scores: list[EnergyScoreRecord] = Field(default_factory=list)
    decision_outcomes: list[DecisionOutcome] = Field(default_factory=list)
    repair_requests: list[RepairRequest] = Field(default_factory=list)
    repair_results: list[RepairResultRecord] = Field(default_factory=list)
    retry_budget: RetryBudget = Field(default_factory=RetryBudget)
    cost_budget: CostBudget = Field(default_factory=CostBudget)
    trace_events: list[TraceEvent] = Field(default_factory=list)
    node_spans: list[NodeSpan] = Field(default_factory=list)
    decision_ledger_entries: list[DecisionLedgerEntry] = Field(default_factory=list)
    errors: list[ErrorRecord] = Field(default_factory=list)
    final_answer: str | None = None
    energy_card: EnergyCard | None = None
    energy_card_v2: EnergyCardV2 | None = None
    final_projection: FinalAnswerProjection | None = None
    human_action_request: HumanActionRequest | None = None
    human_action_result: HumanActionRequest | None = None
    human_action_turn: int = Field(default=0, ge=0)
    status: GraphStatus = "received"

    @model_validator(mode="after")
    def state_links_must_be_valid(self) -> EnergyChatGraphState:
        candidate_ids = {candidate.candidate_id for candidate in self.candidate_versions}
        if self.active_candidate_id is not None and self.active_candidate_id not in candidate_ids:
            raise ValueError("active_candidate_id must reference a retained candidate version")
        unknown_validations = {
            item.candidate_id for item in self.citation_validations
        } - candidate_ids
        if unknown_validations:
            raise ValueError("citation validation must reference a retained candidate")
        return self


RecordT = TypeVar("RecordT", bound=BaseModel)


def append_unique_records(
    current: Sequence[RecordT], incoming: Sequence[RecordT], *, id_field: str
) -> list[RecordT]:
    """Append immutable records while making identical retries idempotent."""

    result = list(current)
    by_id = {_record_id(record, id_field): record for record in result}
    if len(by_id) != len(result):
        raise ValueError(f"Existing records contain duplicate {id_field} values")
    for record in incoming:
        record_id = _record_id(record, id_field)
        existing = by_id.get(record_id)
        if existing is None:
            result.append(record)
            by_id[record_id] = record
        elif existing != record:
            raise ValueError(f"Conflicting record for {id_field}={record_id}")
    return result


def append_unique_values(current: Sequence[str], incoming: Sequence[str]) -> list[str]:
    return list(dict.fromkeys([*current, *incoming]))


def build_trace_event(
    state: EnergyChatGraphState,
    *,
    event_type: str,
    producer: str,
    payload: dict[str, Any],
    event_key: str | None = None,
) -> TraceEvent:
    event_id = f"{state.trace_id}:{event_key or event_type}"
    existing = next((event for event in state.trace_events if event.event_id == event_id), None)
    if existing is not None:
        return existing
    next_sequence = max((event.sequence for event in state.trace_events), default=0) + 1
    return TraceEvent(
        event_id=event_id,
        event_type=event_type,
        producer=producer,
        sequence=next_sequence,
        payload=payload,
    )


def validated_state_update(
    state: EnergyChatGraphState, **updates: object
) -> EnergyChatGraphState:
    payload = state.model_dump(mode="python")
    payload.update(updates)
    return EnergyChatGraphState.model_validate(payload)


def serialize_graph_state(state: EnergyChatGraphState) -> str:
    return json.dumps(
        state.model_dump(mode="json", exclude_unset=True),
        sort_keys=True,
        separators=(",", ":"),
    )


def deserialize_graph_state(payload: str | bytes) -> EnergyChatGraphState:
    raw = json.loads(payload)
    version = raw.get("schema_version") if isinstance(raw, dict) else None
    if version != GRAPH_STATE_SCHEMA_VERSION:
        raise ValueError(f"Unsupported Energy Chat graph state schema: {version!r}")
    return EnergyChatGraphState.model_validate(raw)


def _record_id(record: BaseModel, id_field: str) -> str:
    value = getattr(record, id_field, None)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Record is missing a non-empty {id_field}")
    return value
