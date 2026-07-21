"""Application-lifetime runtime container for Energy Aware Chat V2."""

from __future__ import annotations

import json
from dataclasses import dataclass
from threading import RLock
from typing import Any

from langgraph.types import Command

from app.energy_chat.api_v2_contracts import (
    EnergyChatV2HumanResumeRequest,
    EnergyChatV2Request,
    EnergyChatV2Response,
    EnergyChatV2ThreadStateResponse,
    ExecutionProfile,
    IDFactory,
    UUID4IDFactory,
)
from app.energy_chat.candidate_provider import DeterministicCandidateProvider, ProviderBudget
from app.energy_chat.graph_application import project_v2_response, run_graph_chat_v2
from app.energy_chat.graph_checkpoint import InMemoryCheckpointer
from app.energy_chat.graph_runtime import build_energy_chat_graph
from app.energy_chat.graph_state import EnergyChatGraphState
from app.energy_chat.human_gate import HumanActionRequest, validate_human_action


class ThreadCheckpointNotFoundError(LookupError):
    """Raised when a public thread has no application-lifetime checkpoint."""


class ThreadCheckpointConflictError(RuntimeError):
    """Raised when a completed thread is reused with a different request."""


class HumanActionAlreadyResumedError(RuntimeError):
    """Raised when a completed human interrupt is resumed more than once."""


@dataclass(frozen=True)
class ThreadExecutionRecord:
    """Minimum metadata needed to safely project one stored checkpoint."""

    request: EnergyChatV2Request
    execution_profile: ExecutionProfile
    request_fingerprint: str


@dataclass
class HumanThreadSession:
    """Process-local metadata for one deterministic human interrupt lifecycle."""

    request: EnergyChatV2Request
    request_fingerprint: str
    pending_action: HumanActionRequest | None
    completed: bool = False


class EnergyChatApplicationRuntime:
    """Replaceable process-local owner of checkpoints and human sessions."""

    def __init__(
        self,
        *,
        checkpointer: InMemoryCheckpointer | None = None,
        id_factory: IDFactory | None = None,
    ) -> None:
        self.checkpointer = checkpointer or InMemoryCheckpointer()
        self.id_factory = id_factory or UUID4IDFactory()
        self._records: dict[str, ThreadExecutionRecord] = {}
        self._human_sessions: dict[str, HumanThreadSession] = {}
        self._lock = RLock()

    def execute(
        self,
        request: EnergyChatV2Request,
        execution_profile: ExecutionProfile,
    ) -> EnergyChatV2Response:
        """Execute once or replay an identical completed thread request."""

        materialized = self._materialize_request(request, execution_profile)
        fingerprint = _request_fingerprint(materialized, execution_profile)
        thread_id = _required_thread_id(materialized)

        with self._lock:
            self._reject_human_thread_collision(thread_id)
            existing = self._records.get(thread_id)
            if existing is not None:
                if existing.request_fingerprint != fingerprint:
                    raise ThreadCheckpointConflictError(
                        "Thread already has a different completed request. "
                        "Use a new thread_id for a new request."
                    )
                return self._replay_locked(thread_id, existing)

            response = run_graph_chat_v2(
                materialized,
                execution_profile=execution_profile,
                id_factory=self.id_factory,
                checkpointer=self.checkpointer,
            )
            if self.checkpointer.get_state(thread_id) is None:
                raise RuntimeError("Graph execution completed without a readable checkpoint")
            self._records[thread_id] = ThreadExecutionRecord(
                request=materialized,
                execution_profile=execution_profile,
                request_fingerprint=fingerprint,
            )
            return response

    def execute_human(self, request: EnergyChatV2Request) -> EnergyChatV2Response:
        """Start one deterministic graph that may interrupt for human action."""

        materialized = self._materialize_request(request, "deterministic").model_copy(
            update={"human_gate": True}
        )
        fingerprint = _request_fingerprint(materialized, "deterministic")
        thread_id = _required_thread_id(materialized)

        with self._lock:
            if thread_id in self._records:
                raise ThreadCheckpointConflictError(
                    "Thread already belongs to a non-human execution. Use a new thread_id."
                )
            existing = self._human_sessions.get(thread_id)
            if existing is not None:
                if existing.request_fingerprint != fingerprint:
                    raise ThreadCheckpointConflictError(
                        "Thread already has a different human-gated request."
                    )
                return self._project_human_session(thread_id, existing, replayed=True)

            state = EnergyChatGraphState(
                thread_id=thread_id,
                request_id=_required_request_id(materialized),
                trace_id=_required_trace_id(materialized),
                user_request=materialized.user_message,
                mode=materialized.mode,
                policy_version="unresolved",
                constraints=materialized.required_constraints,
            )
            graph = self._human_graph()
            config = self.checkpointer.config(thread_id)
            result = graph.invoke(state.model_dump(mode="python"), config)
            pending = _pending_human_action(graph.get_state(config))
            domain = _domain_state(result, pending_action=pending)
            self._human_sessions[thread_id] = HumanThreadSession(
                request=materialized,
                request_fingerprint=fingerprint,
                pending_action=pending,
                completed=pending is None,
            )
            return project_v2_response(
                domain,
                materialized,
                "deterministic",
                checkpoint_id=self.checkpointer.get_checkpoint_id(thread_id),
            ).model_copy(update={"human_action_request": pending})

    def resume_human(
        self,
        thread_id: str,
        submission: EnergyChatV2HumanResumeRequest,
    ) -> EnergyChatV2Response:
        """Validate and resume one authoritative pending human interrupt."""

        with self._lock:
            session = self._human_sessions.get(thread_id)
            if session is None:
                raise ThreadCheckpointNotFoundError(thread_id)
            if session.completed or session.pending_action is None:
                raise HumanActionAlreadyResumedError(thread_id)

            pending = session.pending_action
            action = HumanActionRequest(
                action_id=submission.action_id,
                action=submission.action,
                reason=pending.reason,
                expected_revision=submission.expected_revision,
                actor=submission.actor,
                payload=submission.payload,
            )
            validate_human_action(
                action,
                current_revision=pending.expected_revision,
                expected_action_id=pending.action_id,
                expected_action=pending.action,
            )

            graph = self._human_graph()
            config = self.checkpointer.config(thread_id)
            result = graph.invoke(Command(resume=action), config)
            domain = _domain_state(result)
            session.pending_action = None
            session.completed = True
            return project_v2_response(
                domain,
                session.request,
                "deterministic",
                checkpoint_id=self.checkpointer.get_checkpoint_id(thread_id),
            )

    def get_thread_state(self, thread_id: str) -> EnergyChatV2ThreadStateResponse:
        """Return safe metadata for the latest process-local checkpoint."""

        with self._lock:
            human_session = self._human_sessions.get(thread_id)
            if human_session is not None:
                state = self.checkpointer.get_state(thread_id)
                if state is None:
                    raise ThreadCheckpointNotFoundError(thread_id)
                pending = human_session.pending_action
                return _thread_state_response(
                    state,
                    checkpoint_id=self.checkpointer.get_checkpoint_id(thread_id),
                    pending_action=pending,
                )

            self._require_record(thread_id)
            state = self.checkpointer.get_state(thread_id)
            if state is None:
                raise ThreadCheckpointNotFoundError(thread_id)
            return _thread_state_response(
                state,
                checkpoint_id=self.checkpointer.get_checkpoint_id(thread_id),
            )

    def replay(self, thread_id: str) -> EnergyChatV2Response:
        """Project the saved checkpoint without invoking graph or provider code."""

        with self._lock:
            human_session = self._human_sessions.get(thread_id)
            if human_session is not None:
                return self._project_human_session(thread_id, human_session, replayed=True)
            record = self._require_record(thread_id)
            return self._replay_locked(thread_id, record)

    def _project_human_session(
        self,
        thread_id: str,
        session: HumanThreadSession,
        *,
        replayed: bool,
    ) -> EnergyChatV2Response:
        state = self.checkpointer.get_state(thread_id)
        if state is None:
            raise ThreadCheckpointNotFoundError(thread_id)
        pending = session.pending_action
        domain = state.model_copy(
            update={
                "status": "awaiting_human" if pending else state.status,
                "human_action_request": pending,
                "human_action_turn": (
                    pending.expected_revision if pending else state.human_action_turn
                ),
            }
        )
        return project_v2_response(
            domain,
            session.request,
            "deterministic",
            checkpoint_id=self.checkpointer.get_checkpoint_id(thread_id),
            replayed_from_checkpoint=replayed,
        ).model_copy(update={"human_action_request": pending})

    def _replay_locked(
        self,
        thread_id: str,
        record: ThreadExecutionRecord,
    ) -> EnergyChatV2Response:
        state = self.checkpointer.get_state(thread_id)
        if state is None:
            raise ThreadCheckpointNotFoundError(thread_id)
        return project_v2_response(
            state,
            record.request,
            record.execution_profile,
            checkpoint_id=self.checkpointer.get_checkpoint_id(thread_id),
            replayed_from_checkpoint=True,
        )

    def _require_record(self, thread_id: str) -> ThreadExecutionRecord:
        record = self._records.get(thread_id)
        if record is None:
            raise ThreadCheckpointNotFoundError(thread_id)
        return record

    def _reject_human_thread_collision(self, thread_id: str) -> None:
        if thread_id in self._human_sessions:
            raise ThreadCheckpointConflictError(
                "Thread already belongs to a human-gated execution."
            )

    def _human_graph(self):
        return build_energy_chat_graph(
            provider=DeterministicCandidateProvider(),
            budget=ProviderBudget(),
            checkpointer=self.checkpointer.langgraph_saver,
            human_gate_mode="required",
        )

    def _materialize_request(
        self,
        request: EnergyChatV2Request,
        execution_profile: ExecutionProfile,
    ) -> EnergyChatV2Request:
        return request.model_copy(
            update={
                "thread_id": request.thread_id or self.id_factory.new_thread_id(),
                "request_id": request.request_id or self.id_factory.new_request_id(),
                "trace_id": request.trace_id or self.id_factory.new_trace_id(),
                "execution_profile": execution_profile,
            }
        )


def _pending_human_action(snapshot: Any) -> HumanActionRequest | None:
    for task in getattr(snapshot, "tasks", ()):
        for pending_interrupt in getattr(task, "interrupts", ()):
            value = getattr(pending_interrupt, "value", pending_interrupt)
            return HumanActionRequest.model_validate(value)
    return None


def _domain_state(
    result: dict[str, Any],
    *,
    pending_action: HumanActionRequest | None = None,
) -> EnergyChatGraphState:
    payload = {
        field_name: result[field_name]
        for field_name in EnergyChatGraphState.model_fields
        if field_name in result
    }
    if pending_action is not None:
        payload.update(
            {
                "status": "awaiting_human",
                "human_action_request": pending_action,
                "human_action_turn": pending_action.expected_revision,
            }
        )
    return EnergyChatGraphState.model_validate(payload)


def _thread_state_response(
    state: EnergyChatGraphState,
    *,
    checkpoint_id: str | None,
    pending_action: HumanActionRequest | None = None,
) -> EnergyChatV2ThreadStateResponse:
    return EnergyChatV2ThreadStateResponse(
        thread_id=state.thread_id,
        request_id=state.request_id,
        trace_id=state.trace_id,
        checkpoint_id=checkpoint_id,
        graph_status="awaiting_human" if pending_action else state.status,
        awaiting_evidence=state.status == "awaiting_evidence",
        candidate_count=len(state.candidate_versions),
        provider_call_count=len(state.provider_metrics),
        ledger_entry_ids=[
            item.ledger_entry_id for item in state.decision_ledger_entries
        ],
        human_action_pending=pending_action is not None,
        human_action_request=pending_action,
        process_local=True,
        restart_persistent=False,
    )


def _required_thread_id(request: EnergyChatV2Request) -> str:
    assert request.thread_id is not None
    return request.thread_id


def _required_request_id(request: EnergyChatV2Request) -> str:
    assert request.request_id is not None
    return request.request_id


def _required_trace_id(request: EnergyChatV2Request) -> str:
    assert request.trace_id is not None
    return request.trace_id


def _request_fingerprint(
    request: EnergyChatV2Request,
    execution_profile: ExecutionProfile,
) -> str:
    payload = request.model_dump(
        mode="json",
        exclude={"request_id", "trace_id"},
        exclude_none=True,
    )
    payload["execution_profile"] = execution_profile
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
