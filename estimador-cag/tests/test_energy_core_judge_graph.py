from __future__ import annotations

import inspect
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver

from energy_core.judge_graph import GRAPH_VERSION, build_judge_graph, judge_input

SPEC = Path(".energy/specs/0001-energy-policy-ledger")


def _candidate(*, complete: bool) -> dict[str, object]:
    return {
        "candidate_id": "candidate-complete" if complete else "candidate-repair",
        "spec_id": "0001-energy-policy-ledger",
        "energy_before": 500,
        "changed_files": ["energy_core/judge_graph.py"],
        "required_artifacts": ["energy_core/judge_graph.py"],
        "present_artifacts": ["energy_core/judge_graph.py"] if complete else [],
    }


def _input(proposals: list[dict[str, object]], *, run_id: str, max_iterations: int = 2):
    return judge_input(
        run_id=run_id,
        spec_id="0001-energy-policy-ledger",
        policy_path=SPEC / "energy-policy.yaml",
        evidence_path=SPEC / "evidence.jsonl",
        proposals=proposals,
        max_iterations=max_iterations,
    )


def test_graph_accepts_with_typed_state_trace_and_checkpoint() -> None:
    saver = InMemorySaver()
    graph = build_judge_graph(checkpointer=saver)
    config = {"configurable": {"thread_id": "thread-accept"}}

    result = graph.invoke(_input([_candidate(complete=True)], run_id="run-accept"), config)
    snapshot = graph.get_state(config)

    assert result["graph_version"] == GRAPH_VERSION
    assert result["status"] == "accept"
    assert result["iteration"] == 1
    assert result["execution_performed"] is False
    assert [entry["node"] for entry in result["trace"]] == [
        "initialize",
        "propose",
        "evaluate",
        "record",
        "finalize",
    ]
    assert snapshot.values["run_id"] == "run-accept"
    assert snapshot.next == ()


def test_graph_repairs_then_accepts_with_bounded_loop() -> None:
    graph = build_judge_graph(checkpointer=InMemorySaver())
    result = graph.invoke(
        _input(
            [_candidate(complete=False), _candidate(complete=True)],
            run_id="run-repair",
        ),
        {"configurable": {"thread_id": "thread-repair"}},
    )

    assert [decision["decision"] for decision in result["decisions"]] == [
        "repair",
        "accept",
    ]
    assert result["iteration"] == 2
    assert result["status"] == "accept"


def test_graph_stops_when_repair_budget_is_exhausted() -> None:
    graph = build_judge_graph(checkpointer=InMemorySaver())
    result = graph.invoke(
        _input([_candidate(complete=False)], run_id="run-bounded", max_iterations=1),
        {"configurable": {"thread_id": "thread-bounded"}},
    )

    assert result["status"] == "repair"
    assert result["bounded_loop_exhausted"] is True
    assert result["iteration"] == 1


def test_graph_interrupts_and_resumes_from_checkpoint() -> None:
    graph = build_judge_graph(
        checkpointer=InMemorySaver(),
        interrupt_before=["finalize"],
    )
    config = {"configurable": {"thread_id": "thread-resume"}}
    interrupted = graph.invoke(_input([_candidate(complete=True)], run_id="run-resume"), config)
    snapshot = graph.get_state(config)

    assert snapshot.next == ("finalize",)
    assert interrupted.get("status") is None

    resumed = graph.invoke(None, config)

    assert resumed["status"] == "accept"
    assert graph.get_state(config).next == ()


def test_graph_has_no_execution_adapter_or_shell_calls() -> None:
    import energy_core.judge_graph as module

    source = inspect.getsource(module)

    assert "subprocess" not in source
    assert "os.system" not in source
    assert "execution_performed\": True" not in source


def test_checkpoint_threads_are_isolated() -> None:
    graph = build_judge_graph(checkpointer=InMemorySaver())
    first = {"configurable": {"thread_id": "thread-one"}}
    second = {"configurable": {"thread_id": "thread-two"}}

    graph.invoke(_input([_candidate(complete=True)], run_id="run-one"), first)
    graph.invoke(_input([_candidate(complete=False)], run_id="run-two"), second)

    assert graph.get_state(first).values["run_id"] == "run-one"
    assert graph.get_state(first).values["status"] == "accept"
    assert graph.get_state(second).values["run_id"] == "run-two"
    assert graph.get_state(second).values["status"] == "repair"
