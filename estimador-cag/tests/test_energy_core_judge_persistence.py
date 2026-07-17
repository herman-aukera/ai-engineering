from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from langgraph.types import Command

from energy_core.judge_graph import judge_input
from energy_core.judge_persistence import sqlite_judge_graph

SPEC = Path(".energy/specs/0001-energy-policy-ledger")


def _candidate() -> dict[str, object]:
    return {
        "candidate_id": "candidate-persistent",
        "spec_id": "0001-energy-policy-ledger",
        "energy_before": 500,
        "changed_files": ["energy_core/judge_persistence.py"],
        "required_artifacts": ["energy_core/judge_persistence.py"],
        "present_artifacts": ["energy_core/judge_persistence.py"],
    }


def _input(*, conflict: bool = False) -> dict[str, object]:
    payload = judge_input(
        run_id="run-persistent",
        thread_id="thread-persistent",
        spec_id="0001-energy-policy-ledger",
        policy_path=SPEC / "energy-policy.yaml",
        evidence_path=SPEC / "evidence.jsonl",
        proposals=[_candidate()],
        max_iterations=1,
    )
    if conflict:
        payload["evidence"][0]["status"] = "conflict"
    return payload


def test_sqlite_checkpoint_survives_graph_and_connection_restart(tmp_path: Path) -> None:
    database = tmp_path / "judge.sqlite"
    config = {"configurable": {"thread_id": "thread-persistent"}}

    with sqlite_judge_graph(database) as graph:
        result = graph.invoke(_input(), config)
        assert result["status"] == "accept"

    with sqlite_judge_graph(database) as restarted:
        snapshot = restarted.get_state(config)

    assert snapshot.values["run_id"] == "run-persistent"
    assert snapshot.values["status"] == "accept"
    assert snapshot.next == ()


def test_sqlite_schema_setup_is_idempotent_and_preserves_threads(tmp_path: Path) -> None:
    database = tmp_path / "judge.sqlite"
    config = {"configurable": {"thread_id": "thread-persistent"}}
    with sqlite_judge_graph(database) as graph:
        graph.invoke(_input(), config)
    with sqlite_judge_graph(database) as graph:
        assert graph.get_state(config).values["status"] == "accept"

    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

    assert {"checkpoints", "writes"}.issubset(tables)


def test_escalation_interrupt_payload_resumes_after_process_restart(tmp_path: Path) -> None:
    database = tmp_path / "judge.sqlite"
    config = {"configurable": {"thread_id": "thread-persistent"}}
    with sqlite_judge_graph(database) as graph:
        interrupted = graph.invoke(_input(conflict=True), config)

    interrupt_value = interrupted["__interrupt__"][0].value
    assert interrupt_value["kind"] == "human_review"
    assert interrupt_value["route"] == "escalate"
    assert interrupt_value["execution_performed"] is False

    with sqlite_judge_graph(database) as restarted:
        resumed = restarted.invoke(
            Command(resume={"action": "acknowledge", "note": "reviewed"}),
            config,
        )

    assert resumed["status"] == "escalate"
    assert resumed["human_reviewed"] is True
    assert resumed["human_response"]["note"] == "reviewed"
    assert resumed["execution_performed"] is False


def test_missing_evidence_uses_clarify_interrupt_payload(tmp_path: Path) -> None:
    database = tmp_path / "judge.sqlite"
    config = {"configurable": {"thread_id": "thread-persistent"}}
    payload = _input()
    payload["evidence"] = [
        record for record in payload["evidence"] if record["type"] != "pytest_output"
    ]

    with sqlite_judge_graph(database) as graph:
        interrupted = graph.invoke(payload, config)
        interrupt_value = interrupted["__interrupt__"][0].value
        resumed = graph.invoke(
            Command(
                resume={"action": "provide_context", "note": "pytest evidence is pending"}
            ),
            config,
        )

    assert interrupt_value["route"] == "clarify"
    assert interrupt_value["decision"] == "repair"
    assert resumed["status"] == "repair"
    assert resumed["human_reviewed"] is True


def test_persistent_graph_cli_runs_then_inspects_thread(tmp_path: Path) -> None:
    database = tmp_path / "judge.sqlite"
    proposals = tmp_path / "proposals.json"
    proposals.write_text(json.dumps([_candidate()]), encoding="utf-8")
    command = [
        sys.executable,
        "-m",
        "energy_core.judge_graph_cli",
        "run",
        "--database",
        str(database),
        "--thread-id",
        "thread-cli",
        "--run-id",
        "run-cli",
        "--spec-id",
        "0001-energy-policy-ledger",
        "--policy",
        str(SPEC / "energy-policy.yaml"),
        "--evidence",
        str(SPEC / "evidence.jsonl"),
        "--proposals",
        str(proposals),
        "--max-iterations",
        "1",
    ]

    run = subprocess.run(command, text=True, capture_output=True, check=True)
    inspect = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.judge_graph_cli",
            "inspect",
            "--database",
            str(database),
            "--thread-id",
            "thread-cli",
        ],
        text=True,
        capture_output=True,
        check=True,
    )

    assert json.loads(run.stdout)["status"] == "accept"
    inspected = json.loads(inspect.stdout)
    assert inspected["values"]["run_id"] == "run-cli"
    assert inspected["next"] == []
