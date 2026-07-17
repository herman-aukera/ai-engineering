from app.energy_chat.agent import run_energy_aware_chat_agent
from app.energy_chat.contracts import EnergyAwareChatAgentRequest
from app.energy_chat.graph_runtime import build_energy_chat_graph, run_energy_chat_graph
from app.energy_chat.graph_state import EnergyChatGraphState


def _initial(*, request: str, mode: str = "project") -> EnergyChatGraphState:
    return EnergyChatGraphState(
        thread_id="thread-1",
        request_id="request-1",
        trace_id="trace-1",
        user_request=request,
        mode=mode,
        policy_version="unresolved",
        constraints=["deployment evidence"],
    )


def test_graph_declares_explicit_domain_nodes_and_conditional_routes() -> None:
    graph = build_energy_chat_graph()
    topology = graph.get_graph()

    assert {
        "interpret_request",
        "load_policy_and_constraints",
        "determine_evidence_need",
        "skip_evidence",
        "retrieve_project_evidence",
        "await_external_evidence",
        "generate_candidate",
        "run_critic_panel",
        "calculate_energy",
        "decide_candidate",
    } <= set(topology.nodes)


def test_project_graph_path_matches_existing_deterministic_agent() -> None:
    request = EnergyAwareChatAgentRequest(
        user_message="Is deployment evidence required for final-project readiness?",
        mode="project",
        required_constraints=["deployment evidence"],
    )
    expected = run_energy_aware_chat_agent(request)

    state = run_energy_chat_graph(
        EnergyChatGraphState(
            thread_id="thread-1",
            request_id="request-1",
            trace_id="trace-1",
            user_request=request.user_message,
            mode=request.mode,
            policy_version="unresolved",
            constraints=request.required_constraints,
        )
    )

    assert state.status == "evaluated"
    assert state.project_rag == expected.rag
    assert state.candidate_versions[-1].answer == expected.draft_answer
    assert state.energy_scores[-1].score == expected.evaluation.score
    assert state.decision_outcomes[-1].disposition == expected.evaluation.decision.decision


def test_stable_chat_lite_path_skips_retrieval_and_completes() -> None:
    state = run_energy_chat_graph(
        _initial(request="Rewrite this sentence clearly.", mode="chat_lite")
    )

    assert state.status == "evaluated"
    assert state.project_rag is None
    assert state.source_need is not None
    assert state.source_need.decision == "sources_not_required"
    assert state.candidate_versions


def test_current_research_path_stops_for_external_evidence() -> None:
    state = run_energy_chat_graph(
        _initial(request="What is the current API version?", mode="research")
    )

    assert state.status == "awaiting_evidence"
    assert state.candidate_versions == []
    assert state.decision_outcomes == []
    assert state.trace_events[-1].payload["route"] == "external_required"


def test_graph_nodes_emit_deltas_without_identity_rewrites() -> None:
    graph = build_energy_chat_graph()
    updates = list(
        graph.stream(
            _initial(request="Rewrite this sentence clearly.", mode="chat_lite").model_dump(
                mode="python"
            ),
            stream_mode="updates",
        )
    )

    assert updates
    for update in updates:
        for delta in update.values():
            assert not {"thread_id", "request_id", "trace_id"} & set(delta)


def test_complete_graph_replay_does_not_duplicate_accumulated_records() -> None:
    first = run_energy_chat_graph(
        _initial(request="Is deployment evidence required?", mode="project")
    )
    replayed = run_energy_chat_graph(first)

    assert replayed.candidate_versions == first.candidate_versions
    assert replayed.provider_metrics == first.provider_metrics
    assert replayed.critic_panels == first.critic_panels
    assert replayed.energy_scores == first.energy_scores
    assert replayed.decision_outcomes == first.decision_outcomes
    assert replayed.trace_events == first.trace_events
