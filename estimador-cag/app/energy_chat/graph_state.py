"""Versioned, product-local state contracts for Energy Aware Chat orchestration.

This module defines domain truth only.  It deliberately has no LangGraph import so
state invariants, persistence fixtures, and reducer behavior remain independently
testable before a graph runtime is introduced.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.energy_chat.contracts import CriticFinding, EnergyCard, EnergyScore, Mode

GRAPH_STATE_SCHEMA_VERSION = "1.0.0"
GRAPH_STATE_CONTRACT_VERSION = "1.0.0"

GraphStatus = Literal[
    "received",
    "interpreted",
    "policy_ready",
    "evidence_ready",
    "candidate_ready",
    "evaluated",
    "awaiting_human",
    "completed",
    "failed",
]
Disposition = Literal["accept", "repair", "clarify", "reject", "refuse", "escalate"]


class GraphStateRecord(BaseModel):
    """Strict base for records that can cross a checkpoint boundary."""

    model_config = ConfigDict(extra="forbid")


class CandidateVersion(GraphStateRecord):
    """Immutable answer candidate retained for evaluation and repair history."""

    candidate_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    answer: str
    producer: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)


class EnergyScoreRecord(GraphStateRecord):
    """A score tied to the exact candidate that was evaluated."""

    score_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    score: EnergyScore


class DecisionOutcome(GraphStateRecord):
    """Deterministic disposition for one scored candidate."""

    decision_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    score_id: str = Field(min_length=1)
    disposition: Disposition
    reason: str = Field(min_length=1)


class RepairRequest(GraphStateRecord):
    """Explicit bounded repair instruction for a candidate."""

    repair_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    instructions: list[str] = Field(min_length=1)


class TraceEvent(GraphStateRecord):
    """User-safe domain event; hidden model reasoning must not be stored here."""

    event_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    producer: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class ErrorRecord(GraphStateRecord):
    """Safe error projection retained for retry and audit decisions."""

    error_id: str = Field(min_length=1)
    producer: str = Field(min_length=1)
    code: str = Field(min_length=1)
    message: str
    retryable: bool = False


class EnergyChatGraphState(GraphStateRecord):
    """Authoritative v1 state for a single Energy Aware Chat request."""

    schema_version: Literal["1.0.0"] = GRAPH_STATE_SCHEMA_VERSION
    contract_version: Literal["1.0.0"] = GRAPH_STATE_CONTRACT_VERSION
    thread_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    user_request: str = Field(min_length=1)
    mode: Mode = "chat_lite"
    policy_version: str = Field(min_length=1)
    constraints: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    candidate_versions: list[CandidateVersion] = Field(default_factory=list)
    active_candidate_id: str | None = None
    critic_findings: list[CriticFinding] = Field(default_factory=list)
    energy_scores: list[EnergyScoreRecord] = Field(default_factory=list)
    decision_outcomes: list[DecisionOutcome] = Field(default_factory=list)
    repair_requests: list[RepairRequest] = Field(default_factory=list)
    trace_events: list[TraceEvent] = Field(default_factory=list)
    errors: list[ErrorRecord] = Field(default_factory=list)
    final_answer: str | None = None
    energy_card: EnergyCard | None = None
    status: GraphStatus = "received"

    @model_validator(mode="after")
    def active_candidate_must_exist(self) -> EnergyChatGraphState:
        if self.active_candidate_id is None:
            return self
        known_ids = {candidate.candidate_id for candidate in self.candidate_versions}
        if self.active_candidate_id not in known_ids:
            raise ValueError("active_candidate_id must reference a retained candidate version")
        return self


RecordT = TypeVar("RecordT", bound=BaseModel)


def append_unique_records(
    current: Sequence[RecordT], incoming: Sequence[RecordT], *, id_field: str
) -> list[RecordT]:
    """Append immutable records while making identical retries idempotent.

    Reusing an identifier with different content is rejected because silently
    replacing append-only history would make checkpoint replay unauditable.
    """

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


def serialize_graph_state(state: EnergyChatGraphState) -> str:
    """Serialize v1 state into stable canonical JSON for fixtures/checkpoints."""

    return json.dumps(
        state.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )


def deserialize_graph_state(payload: str | bytes) -> EnergyChatGraphState:
    """Load a supported graph-state payload without guessing migrations."""

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
