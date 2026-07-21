"""Application-lifetime runtime container for Energy Aware Chat V2."""

from __future__ import annotations

import json
from dataclasses import dataclass
from threading import RLock

from app.energy_chat.api_v2_contracts import (
    EnergyChatV2Request,
    EnergyChatV2Response,
    EnergyChatV2ThreadStateResponse,
    ExecutionProfile,
    IDFactory,
    UUID4IDFactory,
)
from app.energy_chat.graph_application import project_v2_response, run_graph_chat_v2
from app.energy_chat.graph_checkpoint import InMemoryCheckpointer


class ThreadCheckpointNotFoundError(LookupError):
    """Raised when a public thread has no application-lifetime checkpoint."""


class ThreadCheckpointConflictError(RuntimeError):
    """Raised when a completed thread is reused with a different request."""


@dataclass(frozen=True)
class ThreadExecutionRecord:
    """Minimum metadata needed to safely project one stored checkpoint."""

    request: EnergyChatV2Request
    execution_profile: ExecutionProfile
    request_fingerprint: str


class EnergyChatApplicationRuntime:
    """Replaceable process-local owner of V2 checkpoints and replay metadata.

    The container is attached to ``FastAPI.app.state`` by the composition root.
    Tests can replace it without mutating hidden module globals. Replay reads the
    saved graph checkpoint and never submits the original prompt to the graph.
    """

    def __init__(
        self,
        *,
        checkpointer: InMemoryCheckpointer | None = None,
        id_factory: IDFactory | None = None,
    ) -> None:
        self.checkpointer = checkpointer or InMemoryCheckpointer()
        self.id_factory = id_factory or UUID4IDFactory()
        self._records: dict[str, ThreadExecutionRecord] = {}
        self._lock = RLock()

    def execute(
        self,
        request: EnergyChatV2Request,
        execution_profile: ExecutionProfile,
    ) -> EnergyChatV2Response:
        """Execute once or replay an identical completed thread request."""

        materialized = self._materialize_request(request, execution_profile)
        fingerprint = _request_fingerprint(materialized, execution_profile)
        thread_id = materialized.thread_id
        assert thread_id is not None

        with self._lock:
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

    def get_thread_state(self, thread_id: str) -> EnergyChatV2ThreadStateResponse:
        """Return safe metadata for the latest process-local thread checkpoint."""

        with self._lock:
            self._require_record(thread_id)
            state = self.checkpointer.get_state(thread_id)
            if state is None:
                raise ThreadCheckpointNotFoundError(thread_id)
            return EnergyChatV2ThreadStateResponse(
                thread_id=state.thread_id,
                request_id=state.request_id,
                trace_id=state.trace_id,
                checkpoint_id=self.checkpointer.get_checkpoint_id(thread_id),
                graph_status=state.status,
                awaiting_evidence=state.status == "awaiting_evidence",
                candidate_count=len(state.candidate_versions),
                provider_call_count=len(state.provider_metrics),
                ledger_entry_ids=[
                    item.ledger_entry_id for item in state.decision_ledger_entries
                ],
                process_local=True,
                restart_persistent=False,
            )

    def replay(self, thread_id: str) -> EnergyChatV2Response:
        """Project the saved checkpoint without invoking graph or provider code."""

        with self._lock:
            record = self._require_record(thread_id)
            return self._replay_locked(thread_id, record)

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
