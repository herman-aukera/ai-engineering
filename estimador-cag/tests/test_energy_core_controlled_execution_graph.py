from __future__ import annotations

from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver

from energy_core.judge_graph import build_judge_graph, judge_input

SPEC = Path(".energy/specs/0001-energy-policy-ledger")


def _candidate() -> dict[str, object]:
    return {
        "candidate_id": "candidate-command-preview",
        "spec_id": "0001-energy-policy-ledger",
        "energy_before": 500,
        "changed_files": ["energy_core/controlled_execution.py"],
        "required_artifacts": ["energy_core/controlled_execution.py"],
        "present_artifacts": ["energy_core/controlled_execution.py"],
    }


def _command(executable: str = "pytest") -> dict[str, object]:
    return {
        "proposal_id": f"command-{executable}",
        "executable": executable,
        "arguments": [],
        "working_directory": ".",
        "declared_paths": [],
        "requested_mode": "dry_run",
        "timeout_seconds": 30,
        "max_output_chars": 256,
        "environment_names": [],
        "rollback_summary": "No mutation occurs during preview.",
    }


def test_accept_route_builds_dry_run_evidence_and_reevaluates() -> None:
    graph = build_judge_graph(checkpointer=InMemorySaver())
    result = graph.invoke(
        judge_input(
            run_id="run-command-preview",
            spec_id="0001-energy-policy-ledger",
            policy_path=SPEC / "energy-policy.yaml",
            evidence_path=SPEC / "evidence.jsonl",
            proposals=[_candidate()],
            max_iterations=1,
            repository_root=".",
            command_proposal=_command(),
        ),
        {"configurable": {"thread_id": "thread-command-preview"}},
    )

    assert result["status"] == "accept"
    assert result["execution_status"] == "dry_run"
    assert result["execution_performed"] is False
    assert result["execution_plan"]["disposition"] == "allow_fake"
    assert result["execution_evidence"]["adapter_invoked"] is False
    assert result["execution_evidence"]["execution_performed"] is False
    assert result["evidence"][-1]["type"] == "controlled_execution"
    assert [entry["node"] for entry in result["trace"]] == [
        "initialize",
        "propose",
        "evaluate",
        "record",
        "execution_preview",
        "reevaluate_execution",
        "record_execution",
        "finalize",
    ]
    assert [decision["decision"] for decision in result["decisions"]] == [
        "accept",
        "accept",
    ]


def test_denied_command_is_recorded_without_adapter_or_execution() -> None:
    graph = build_judge_graph(checkpointer=InMemorySaver())
    result = graph.invoke(
        judge_input(
            run_id="run-command-denied",
            spec_id="0001-energy-policy-ledger",
            policy_path=SPEC / "energy-policy.yaml",
            evidence_path=SPEC / "evidence.jsonl",
            proposals=[_candidate()],
            max_iterations=1,
            repository_root=".",
            command_proposal=_command("rm"),
        ),
        {"configurable": {"thread_id": "thread-command-denied"}},
    )

    assert result["status"] == "accept"
    assert result["execution_status"] == "denied"
    assert result["execution_plan"]["disposition"] == "deny"
    assert result["execution_evidence"]["status"] == "fail"
    assert result["execution_evidence"]["adapter_invoked"] is False
    assert result["execution_performed"] is False
