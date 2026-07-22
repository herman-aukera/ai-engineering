"""Application service for authoritative human review over a pending graph checkpoint."""

from __future__ import annotations

import json

from langgraph.types import Command

from app.energy_chat.api_v2_contracts import (
    EnergyChatV2HumanResumeRequest,
    EnergyChatV2Response,
)
from app.energy_chat.graph_application import project_v2_response
from app.energy_chat.human_authority import apply_human_authority
from app.energy_chat.human_gate import (
    HumanActionRequest,
    HumanIdempotencyConflictError,
    validate_human_action,
)
from app.energy_chat.runtime_container import (
    EnergyChatApplicationRuntime,
    HumanActionAlreadyResumedError,
    ThreadCheckpointNotFoundError,
    _domain_state,
)


def resume_human_authoritatively(
    runtime: EnergyChatApplicationRuntime,
    thread_id: str,
    submission: EnergyChatV2HumanResumeRequest,
) -> EnergyChatV2Response:
    """Resume, apply reviewer authority, and persist its reducer-safe state delta."""

    with runtime._lock:  # noqa: SLF001 - same bounded application service boundary
        session = runtime._human_sessions.get(thread_id) or runtime._recover_human_session(  # noqa: SLF001
            thread_id
        )
        if session is None:
            raise ThreadCheckpointNotFoundError(thread_id)
        state = runtime.checkpointer.get_state(thread_id)
        if state is None:
            raise ThreadCheckpointNotFoundError(thread_id)

        prior_action = state.human_action_result
        if session.completed or session.pending_action is None:
            if prior_action is None:
                raise HumanActionAlreadyResumedError(thread_id)
            replay_action = _build_action(submission, prior_action)
            if _action_fingerprint(replay_action) != _action_fingerprint(prior_action):
                if replay_action.idempotency_key == prior_action.idempotency_key:
                    raise HumanIdempotencyConflictError(
                        "The human idempotency key was reused with different review content"
                    )
                raise HumanActionAlreadyResumedError(thread_id)
            return runtime._project_human_session(  # noqa: SLF001
                thread_id,
                session,
                replayed=True,
            ).model_copy(update={"human_decision": prior_action.decision})

        pending = session.pending_action
        action = _build_action(submission, pending)
        validate_human_action(
            action,
            current_revision=pending.expected_revision,
            expected_action_id=pending.action_id,
            expected_action=pending.action,
        )

        graph = runtime._human_graph()  # noqa: SLF001
        config = runtime.checkpointer.config(thread_id)
        result = graph.invoke(Command(resume=action), config)
        domain = _domain_state(result)
        authority = apply_human_authority(domain, action)
        graph.update_state(
            config,
            authority.checkpoint_update,
            as_node="build_final_projection",
        )
        persisted = runtime.checkpointer.get_state(thread_id) or authority.state
        session.pending_action = None
        session.completed = True
        return project_v2_response(
            persisted.model_copy(update={"status": "completed"}),
            session.request,
            "deterministic",
            checkpoint_id=runtime.checkpointer.get_checkpoint_id(thread_id),
            restart_persistent=bool(
                getattr(runtime.checkpointer, "restart_persistent", False)
            ),
        ).model_copy(
            update={
                "human_action_request": None,
                "human_decision": action.decision,
            }
        )


def _build_action(
    submission: EnergyChatV2HumanResumeRequest,
    source: HumanActionRequest,
) -> HumanActionRequest:
    return HumanActionRequest(
        action_id=submission.action_id,
        action=submission.action,
        reason=source.reason,
        expected_revision=submission.expected_revision,
        actor=submission.actor,
        decision=submission.decision,
        decision_reason=submission.decision_reason,
        idempotency_key=submission.idempotency_key,
        adjustments=submission.adjustments,
        payload=submission.payload,
    )


def _action_fingerprint(action: HumanActionRequest) -> str:
    return json.dumps(
        action.model_dump(mode="json", exclude_none=True),
        sort_keys=True,
        separators=(",", ":"),
    )
