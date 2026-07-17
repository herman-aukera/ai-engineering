from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from energy_core.execution_authorization import AuthorizationScope
from energy_core.judge_graph import build_judge_graph, judge_input
from energy_core.judge_persistence import sqlite_judge_graph

SPEC = Path(".energy/specs/0001-energy-policy-ledger")


def _candidate() -> dict[str, object]:
    return {
        "candidate_id": "candidate-human-command",
        "spec_id": "0001-energy-policy-ledger",
        "energy_before": 500,
        "changed_files": ["energy_core/execution_authorization.py"],
        "required_artifacts": ["energy_core/execution_authorization.py"],
        "present_artifacts": ["energy_core/execution_authorization.py"],
    }


def _command() -> dict[str, object]:
    return {
        "proposal_id": "command-git-status",
        "executable": "git",
        "arguments": ["status", "--short"],
        "working_directory": ".",
        "declared_paths": [],
        "requested_mode": "fake",
        "timeout_seconds": 30,
        "max_output_chars": 512,
        "environment_names": [],
        "rollback_summary": "Read-only operation.",
    }


def _input(tmp_path: Path) -> dict[str, object]:
    return judge_input(
        run_id="run-execution-authorization",
        thread_id="thread-execution-authorization",
        spec_id="0001-energy-policy-ledger",
        policy_path=SPEC / "energy-policy.yaml",
        evidence_path=SPEC / "evidence.jsonl",
        proposals=[_candidate()],
        max_iterations=1,
        repository_root=tmp_path,
        command_proposal=_command(),
        execution_revision=7,
        trusted_execution_actors=["gonzalo"],
        authorization_now="2026-07-17T20:05:00Z",
    )


def _authorization(interrupt_payload, **overrides):
    created = datetime(2026, 7, 17, 20, 0, tzinfo=UTC)
    payload = {
        "authorization_id": "auth-graph-1",
        "actor": "gonzalo",
        "plan_hash": interrupt_payload["plan_hash"],
        "expected_revision": interrupt_payload["expected_revision"],
        "accepted_revision": interrupt_payload["expected_revision"],
        "scope": AuthorizationScope.model_validate(interrupt_payload["scope"]).model_dump(
            mode="json"
        ),
        "created_at": created.isoformat(),
        "expires_at": (created + timedelta(minutes=10)).isoformat(),
        "nonce": "nonce-graph-123456",
        "reason": "Exact plan reviewed.",
        "rollback_acknowledged": True,
        "consumed": False,
    }
    payload.update(overrides)
    return payload


def test_authorization_interrupt_resumes_after_sqlite_restart(tmp_path: Path) -> None:
    database = tmp_path / "judge.sqlite"
    config = {"configurable": {"thread_id": "thread-execution-authorization"}}

    with sqlite_judge_graph(database) as graph:
        interrupted = graph.invoke(_input(tmp_path), config)

    interrupt_payload = interrupted["__interrupt__"][0].value
    assert interrupt_payload["kind"] == "execution_authorization"
    assert interrupt_payload["expected_revision"] == 7
    assert interrupt_payload["execution_performed"] is False

    with sqlite_judge_graph(database) as restarted:
        resumed = restarted.invoke(
            Command(
                resume={
                    "action": "authorize",
                    "authorization": _authorization(interrupt_payload),
                }
            ),
            config,
        )
        snapshot = restarted.get_state(config)

    assert resumed["status"] == "accept"
    assert resumed["execution_authorized"] is True
    assert resumed["execution_status"] == "authorized"
    assert resumed["execution_authorization"]["consumed"] is True
    assert resumed["authorization_receipt"]["execution_performed"] is False
    assert len(resumed["consumed_nonce_hashes"]) == 1
    assert resumed["execution_performed"] is False
    assert snapshot.next == ()


def test_wrong_plan_hash_fails_closed_at_resume(tmp_path: Path) -> None:
    graph = build_judge_graph(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "thread-wrong-hash"}}
    interrupted = graph.invoke(_input(tmp_path), config)
    interrupt_payload = interrupted["__interrupt__"][0].value

    with pytest.raises(PermissionError, match="plan_hash_mismatch"):
        graph.invoke(
            Command(
                resume={
                    "action": "authorize",
                    "authorization": _authorization(
                        interrupt_payload,
                        plan_hash="0" * 64,
                    ),
                }
            ),
            config,
        )


def test_cancel_records_no_authority_and_no_execution(tmp_path: Path) -> None:
    graph = build_judge_graph(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "thread-cancel-auth"}}
    graph.invoke(_input(tmp_path), config)

    resumed = graph.invoke(
        Command(resume={"action": "cancel", "reason": "Not approved."}),
        config,
    )

    assert resumed["status"] == "accept"
    assert resumed["execution_authorized"] is False
    assert resumed["execution_status"] == "authorization_cancelled"
    assert resumed["execution_performed"] is False
