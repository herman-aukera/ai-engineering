from __future__ import annotations

from time import perf_counter_ns

import pytest
from pydantic import ValidationError
from structlog.testing import capture_logs

from app.schemas.graph_estimation import AgentContributionPayload
from app.services.session14_action_audit import (
    begin_agent_action,
    complete_agent_action,
    record_agent_action_failure,
)


def test_allowed_action_emits_replay_safe_sanitized_audit_envelope() -> None:
    authorization_checks: list[tuple[str, str]] = []

    def authorize(agent_id: str, tool_name: str) -> None:
        authorization_checks.append((agent_id, tool_name))

    with capture_logs() as logs:
        action = begin_agent_action(
            estimation_id="estimate-14",
            agent_id="budget_searcher",
            sequence=2,
            action="search_budgets",
            tool_name="search_budgets",
            validated_input={
                "components": ["CLIENT-SECRET"],
                "budget_matches": [],
                "execution_metadata": {
                    "private": "CLIENT-SECRET",
                },
            },
            authorize=authorize,
        )
        contribution = complete_agent_action(
            action,
            summary="Budget search completed with 0 matches.",
            state_delta_keys=[
                "budget_matches",
                "budget_search_completed",
            ],
        )

    assert authorization_checks == [
        ("budget_searcher", "search_budgets")
    ]
    assert contribution == {
        "contribution_id": "estimate-14:budget_searcher:2",
        "agent_id": "budget_searcher",
        "sequence": 2,
        "summary": "Budget search completed with 0 matches.",
        "state_delta_keys": [
            "agent_contributions",
            "budget_matches",
            "budget_search_completed",
        ],
        "action": "search_budgets",
        "tool_name": "search_budgets",
        "privilege_decision": "allowed",
        "execution_status": "succeeded",
        "validated_input_shape": {
            "budget_matches": "list",
            "components": "list",
            "execution_metadata": "mapping",
        },
        "result_ref": (
            "checkpoint:estimate-14:budget_searcher:2"
        ),
        "duration_ms": contribution["duration_ms"],
    }
    assert contribution["duration_ms"] >= 0
    assert logs[-1]["event"] == "session14_agent_action"
    assert logs[-1]["execution_status"] == "succeeded"
    assert "CLIENT-SECRET" not in repr(contribution)
    assert "CLIENT-SECRET" not in repr(logs)


def test_denied_action_is_audited_before_execution_authority_exists() -> None:
    def deny(agent_id: str, tool_name: str) -> None:
        raise PermissionError(
            f"{agent_id} cannot use {tool_name}: CLIENT-SECRET"
        )

    with capture_logs() as logs:
        with pytest.raises(PermissionError, match="CLIENT-SECRET"):
            begin_agent_action(
                estimation_id="estimate-14",
                agent_id="budget_searcher",
                sequence=2,
                action="validate_estimate",
                tool_name="validate_estimate",
                validated_input={
                    "estimate": "CLIENT-SECRET",
                },
                authorize=deny,
            )

    denied = logs[-1]
    assert denied["event"] == "session14_agent_action"
    assert denied["privilege_decision"] == "denied"
    assert denied["execution_status"] == "denied"
    assert denied["validated_input_shape"] == {
        "estimate": "string",
    }
    assert denied["result_ref"] is None
    assert "CLIENT-SECRET" not in repr(logs)


def test_failed_action_logs_exception_type_without_exception_message() -> None:
    action = begin_agent_action(
        estimation_id="estimate-14",
        agent_id="requirements_extractor",
        sequence=1,
        action="extract_and_classify_requirements",
        tool_name=None,
        validated_input={
            "transcript": "CLIENT-SECRET",
            "execution_metadata": {},
        },
    )

    with capture_logs() as logs:
        record_agent_action_failure(
            action,
            RuntimeError("provider failed with CLIENT-SECRET"),
        )

    failed = logs[-1]
    assert failed["event"] == "session14_agent_action"
    assert failed["privilege_decision"] == "not_applicable"
    assert failed["execution_status"] == "failed"
    assert failed["summary"] == "Action failed with RuntimeError."
    assert failed["result_ref"] is None
    assert "CLIENT-SECRET" not in repr(logs)


def test_audit_duration_never_precedes_action_start() -> None:
    action = begin_agent_action(
        estimation_id="estimate-14",
        agent_id="requirements_extractor",
        sequence=1,
        action="extract_and_classify_requirements",
        tool_name=None,
        validated_input={"transcript": "safe"},
    )

    assert action.started_ns <= perf_counter_ns()


def test_legacy_checkpoint_contribution_receives_safe_defaults() -> None:
    payload = AgentContributionPayload.model_validate(
        {
            "contribution_id": "estimate-14:budget_searcher:2",
            "agent_id": "budget_searcher",
            "sequence": 2,
            "summary": "Budget search completed.",
            "state_delta_keys": ["budget_matches"],
        }
    )

    assert payload.action == "legacy_specialist_action"
    assert payload.tool_name is None
    assert payload.privilege_decision == "not_applicable"
    assert payload.execution_status == "succeeded"
    assert payload.validated_input_shape == {}
    assert payload.result_ref is None
    assert payload.duration_ms == 0


def test_public_audit_contract_rejects_raw_arguments() -> None:
    with pytest.raises(ValidationError):
        AgentContributionPayload.model_validate(
            {
                "contribution_id": (
                    "estimate-14:budget_searcher:2"
                ),
                "agent_id": "budget_searcher",
                "sequence": 2,
                "summary": "Budget search completed.",
                "state_delta_keys": ["budget_matches"],
                "arguments": {
                    "query": "CLIENT-SECRET",
                },
            }
        )
