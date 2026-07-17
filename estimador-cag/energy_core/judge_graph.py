from __future__ import annotations

from operator import add
from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from energy_core.decider import evaluate_candidate
from energy_core.evidence import read_evidence_records
from energy_core.models import CandidateState, EnergyDecision, EnergyPolicy, EvidenceRecord
from energy_core.policy import load_policy

GRAPH_VERSION = "1.0.0"


class JudgeState(TypedDict, total=False):
    """Serializable graph state with explicit authoritative and accumulator fields."""

    graph_version: str
    run_id: str
    thread_id: str
    spec_id: str
    policy_version: str
    policy: dict[str, Any]
    evidence: list[dict[str, Any]]
    proposals: list[dict[str, Any]]
    candidate: dict[str, Any]
    decision: dict[str, Any]
    iteration: int
    max_iterations: int
    status: Literal["accept", "repair", "reject", "escalate"]
    bounded_loop_exhausted: bool
    execution_performed: bool
    human_reviewed: bool
    human_response: dict[str, Any]
    trace: Annotated[list[dict[str, Any]], add]
    decisions: Annotated[list[dict[str, Any]], add]


def judge_input(
    *,
    run_id: str,
    spec_id: str,
    policy_path: str | Path,
    evidence_path: str | Path,
    proposals: list[dict[str, object]],
    max_iterations: int,
    thread_id: str | None = None,
) -> JudgeState:
    """Build JSON-compatible authoritative input for a deterministic judge run."""

    if max_iterations < 1:
        raise ValueError("max_iterations must be at least 1")
    policy = load_policy(policy_path)
    evidence = read_evidence_records(evidence_path)
    return {
        "graph_version": GRAPH_VERSION,
        "run_id": run_id,
        "thread_id": thread_id or run_id,
        "spec_id": spec_id,
        "policy_version": policy.version,
        "policy": policy.model_dump(mode="json"),
        "evidence": [record.model_dump(mode="json") for record in evidence],
        "proposals": [dict(proposal) for proposal in proposals],
        "iteration": 0,
        "max_iterations": max_iterations,
        "bounded_loop_exhausted": False,
        "execution_performed": False,
        "human_reviewed": False,
        "trace": [],
        "decisions": [],
    }


def build_judge_graph(
    *,
    checkpointer: Any,
    interrupt_before: list[str] | None = None,
):
    """Compile the deterministic judge with injected persistence."""

    builder = StateGraph(JudgeState)
    builder.add_node("initialize", _initialize)
    builder.add_node("propose", _propose)
    builder.add_node("evaluate", _evaluate)
    builder.add_node("record", _record)
    builder.add_node("human_review", _human_review)
    builder.add_node("finalize", _finalize)
    builder.add_edge(START, "initialize")
    builder.add_edge("initialize", "propose")
    builder.add_edge("propose", "evaluate")
    builder.add_edge("evaluate", "record")
    builder.add_conditional_edges(
        "record",
        _route_after_record,
        {
            "propose": "propose",
            "human_review": "human_review",
            "finalize": "finalize",
        },
    )
    builder.add_edge("human_review", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_before,
        name="eacode-deterministic-judge",
    )


def _initialize(state: JudgeState) -> JudgeState:
    if state.get("graph_version") != GRAPH_VERSION:
        raise ValueError(f"Unsupported graph version: {state.get('graph_version')}")
    if not state.get("proposals"):
        raise ValueError("At least one deterministic proposal is required.")
    return {
        "execution_performed": False,
        "trace": [_trace("initialize", state, "validated authoritative input")],
    }


def _propose(state: JudgeState) -> JudgeState:
    index = state["iteration"]
    candidate = state["proposals"][index]
    return {
        "candidate": candidate,
        "iteration": index + 1,
        "trace": [_trace("propose", state, f"selected deterministic proposal {index + 1}")],
    }


def _evaluate(state: JudgeState) -> JudgeState:
    policy = EnergyPolicy.model_validate(state["policy"])
    candidate = CandidateState.model_validate(state["candidate"])
    evidence = [EvidenceRecord.model_validate(record) for record in state["evidence"]]
    decision = evaluate_candidate(policy=policy, candidate=candidate, evidence=evidence)
    return {
        "decision": decision.model_dump(mode="json"),
        "trace": [_trace("evaluate", state, f"policy decided {decision.decision}")],
    }


def _record(state: JudgeState) -> JudgeState:
    decision = EnergyDecision.model_validate(state["decision"])
    return {
        "decisions": [decision.model_dump(mode="json")],
        "trace": [_trace("record", state, "accumulated domain decision")],
    }


def _route_after_record(
    state: JudgeState,
) -> Literal["propose", "human_review", "finalize"]:
    can_retry = (
        state["decision"]["decision"] == "repair"
        and state["iteration"] < state["max_iterations"]
        and state["iteration"] < len(state["proposals"])
    )
    if can_retry:
        return "propose"
    decision = state["decision"]
    if decision["decision"] == "escalate" or (
        decision["decision"] == "repair"
        and decision["next_action"] == "add_required_evidence"
    ):
        return "human_review"
    return "finalize"


def _human_review(state: JudgeState) -> JudgeState:
    decision = EnergyDecision.model_validate(state["decision"])
    route = "escalate" if decision.decision == "escalate" else "clarify"
    response = interrupt(
        {
            "kind": "human_review",
            "route": route,
            "run_id": state["run_id"],
            "thread_id": state["thread_id"],
            "decision": decision.decision,
            "reasoning_summary": decision.reasoning_summary,
            "required_repairs": decision.required_repairs,
            "allowed_actions": ["acknowledge", "provide_context", "cancel"],
            "execution_performed": False,
        }
    )
    if not isinstance(response, dict) or response.get("action") not in {
        "acknowledge",
        "provide_context",
        "cancel",
    }:
        raise ValueError("Human response must contain an allowed action.")
    return {
        "human_reviewed": True,
        "human_response": dict(response),
        "execution_performed": False,
        "trace": [_trace("human_review", state, f"human handled {route} route")],
    }


def _finalize(state: JudgeState) -> JudgeState:
    decision = EnergyDecision.model_validate(state["decision"])
    exhausted = (
        decision.decision == "repair"
        and (
            state["iteration"] >= state["max_iterations"]
            or state["iteration"] >= len(state["proposals"])
        )
    )
    return {
        "status": decision.decision,
        "bounded_loop_exhausted": exhausted,
        "execution_performed": False,
        "trace": [_trace("finalize", state, f"completed with {decision.decision}")],
    }


def _trace(node: str, state: JudgeState, detail: str) -> dict[str, Any]:
    return {
        "node": node,
        "run_id": state["run_id"],
        "thread_id": state["thread_id"],
        "iteration": state.get("iteration", 0),
        "detail": detail,
    }
