"""Replay-safe, sanitized Session 14 specialist action auditing."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from time import perf_counter_ns
from typing import Literal

import structlog

from app.generation.graph.review_state import (
    AgentContribution,
    Session14AgentId,
)
from app.services.session14_privileges import (
    BusinessTool,
    assert_tool_allowed,
)

log = structlog.get_logger("session14_action_audit")

ActionAuthorizer = Callable[
    [Session14AgentId, BusinessTool],
    None,
]
PrivilegeDecision = Literal[
    "allowed",
    "not_applicable",
    "denied",
]
ActionExecutionStatus = Literal[
    "succeeded",
    "denied",
    "failed",
]


@dataclass(frozen=True)
class AgentActionContext:
    """Validated metadata retained while one specialist action executes."""

    contribution_id: str
    estimation_id: str
    agent_id: Session14AgentId
    sequence: int
    action: str
    tool_name: BusinessTool | None
    privilege_decision: PrivilegeDecision
    validated_input_shape: dict[str, str]
    started_ns: int


def _safe_shape(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, Mapping):
        return "mapping"
    if isinstance(value, list):
        return "list"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return type(value).__name__


def _validated_input_shape(
    validated_input: Mapping[str, object],
) -> dict[str, str]:
    """Describe validated argument structure without retaining values."""

    return {
        key: _safe_shape(validated_input[key])
        for key in sorted(validated_input)
    }


def _duration_ms(started_ns: int) -> int:
    return max(0, perf_counter_ns() - started_ns) // 1_000_000


def _result_ref(context: AgentActionContext) -> str:
    return f"checkpoint:{context.contribution_id}"


def _record(
    context: AgentActionContext,
    *,
    summary: str,
    state_delta_keys: list[str],
    execution_status: ActionExecutionStatus,
    result_ref: str | None,
) -> AgentContribution:
    return AgentContribution(
        contribution_id=context.contribution_id,
        agent_id=context.agent_id,
        sequence=context.sequence,
        summary=summary,
        state_delta_keys=sorted(
            {
                *state_delta_keys,
                *(
                    ("agent_contributions",)
                    if execution_status == "succeeded"
                    else ()
                ),
            }
        ),
        action=context.action,
        tool_name=context.tool_name,
        privilege_decision=context.privilege_decision,
        execution_status=execution_status,
        validated_input_shape=dict(
            context.validated_input_shape
        ),
        result_ref=result_ref,
        duration_ms=_duration_ms(context.started_ns),
    )


def _emit(record: AgentContribution) -> None:
    fields = dict(record)
    status = record["execution_status"]

    if status == "denied":
        log.warning("session14_agent_action", **fields)
    elif status == "failed":
        log.error("session14_agent_action", **fields)
    else:
        log.info("session14_agent_action", **fields)


def begin_agent_action(
    *,
    estimation_id: str,
    agent_id: Session14AgentId,
    sequence: int,
    action: str,
    tool_name: BusinessTool | None,
    validated_input: Mapping[str, object],
    authorize: ActionAuthorizer = assert_tool_allowed,
) -> AgentActionContext:
    """Authorize one action and retain only its safe input structure."""

    normalized_estimation_id = estimation_id.strip()
    normalized_action = action.strip()

    if not normalized_estimation_id:
        raise ValueError("estimation_id must not be blank")
    if sequence < 1:
        raise ValueError("sequence must be positive")
    if not normalized_action:
        raise ValueError("action must not be blank")

    context = AgentActionContext(
        contribution_id=(
            f"{normalized_estimation_id}:{agent_id}:{sequence}"
        ),
        estimation_id=normalized_estimation_id,
        agent_id=agent_id,
        sequence=sequence,
        action=normalized_action,
        tool_name=tool_name,
        privilege_decision=(
            "not_applicable" if tool_name is None else "allowed"
        ),
        validated_input_shape=_validated_input_shape(
            validated_input
        ),
        started_ns=perf_counter_ns(),
    )

    if tool_name is None:
        return context

    try:
        authorize(agent_id, tool_name)
    except (PermissionError, ValueError):
        denied_context = replace(
            context,
            privilege_decision="denied",
        )
        _emit(
            _record(
                denied_context,
                summary=(
                    "Action denied by the server-owned "
                    "privilege policy."
                ),
                state_delta_keys=[],
                execution_status="denied",
                result_ref=None,
            )
        )
        raise

    return context


def complete_agent_action(
    context: AgentActionContext,
    *,
    summary: str,
    state_delta_keys: list[str],
) -> AgentContribution:
    """Complete and emit one successful persistent audit record."""

    record = _record(
        context,
        summary=summary,
        state_delta_keys=state_delta_keys,
        execution_status="succeeded",
        result_ref=_result_ref(context),
    )
    _emit(record)
    return record


def record_agent_action_failure(
    context: AgentActionContext,
    error: Exception,
) -> AgentContribution:
    """Emit a failed action without retaining exception text or arguments."""

    record = _record(
        context,
        summary=f"Action failed with {type(error).__name__}.",
        state_delta_keys=[],
        execution_status="failed",
        result_ref=None,
    )
    _emit(record)
    return record
