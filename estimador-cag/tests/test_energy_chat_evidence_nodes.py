from app.energy_chat.contracts import SourceNeedRequest
from app.energy_chat.evidence_nodes import (
    apply_evidence_need_delta,
    apply_evidence_routing_delta,
    determine_evidence_need,
    route_evidence,
)
from app.energy_chat.graph_state import EnergyChatGraphState
from app.energy_chat.source_guard import classify_source_need


def _state(*, request: str, mode: str = "chat_lite", evidence_refs: list[str] | None = None):
    return EnergyChatGraphState(
        thread_id="thread-1",
        request_id="request-1",
        trace_id="trace-1",
        user_request=request,
        mode=mode,
        policy_version="1.0.0",
        evidence_refs=evidence_refs or [],
        status="policy_ready",
    )


def test_evidence_need_node_preserves_existing_classifier_behavior() -> None:
    state = _state(request="Does this branch satisfy the validation gate?", mode="project")

    delta = determine_evidence_need(state)
    expected = classify_source_need(
        SourceNeedRequest(user_message=state.user_request, mode="project")
    )

    assert delta.source_need == expected
    assert delta.status == "evidence_classified"
    assert delta.trace_events[0].payload == {
        "decision": "sources_required",
        "detected_marker_count": len(expected.detected_markers),
        "requires_current_sources": False,
        "requires_project_sources": True,
    }


def test_stable_request_skips_retrieval() -> None:
    state = _state(request="Rewrite this sentence clearly.")
    classified = apply_evidence_need_delta(state, determine_evidence_need(state))

    delta = route_evidence(classified)

    assert delta.route == "skip"
    assert delta.evidence_refs == []
    assert delta.project_rag is None
    assert delta.status == "evidence_ready"


def test_project_request_retrieves_attributable_evidence() -> None:
    state = _state(request="Does this branch satisfy the validation gate?", mode="project")
    classified = apply_evidence_need_delta(state, determine_evidence_need(state))

    ready = apply_evidence_routing_delta(classified, route_evidence(classified, k=2))

    assert ready.project_rag is not None
    assert len(ready.project_rag.results) == 2
    assert ready.evidence_refs == ready.project_rag.evidence_refs
    assert all(ref.startswith("source:") for ref in ready.evidence_refs)
    assert ready.status == "evidence_ready"


def test_current_research_request_requires_external_evidence_without_fabrication() -> None:
    state = _state(request="What is the current API version?", mode="research")
    classified = apply_evidence_need_delta(state, determine_evidence_need(state))

    delta = route_evidence(classified)

    assert delta.route == "external_required"
    assert delta.evidence_refs == []
    assert delta.project_rag is None
    assert delta.status == "awaiting_evidence"


def test_existing_trusted_evidence_skips_retrieval() -> None:
    state = _state(
        request="Does this branch satisfy the validation gate?",
        mode="project",
        evidence_refs=["git:status-clean"],
    )
    classified = apply_evidence_need_delta(state, determine_evidence_need(state))

    assert route_evidence(classified).route == "skip"


def test_evidence_nodes_are_replay_idempotent() -> None:
    state = _state(request="Does this branch satisfy the validation gate?", mode="project")
    classified = apply_evidence_need_delta(state, determine_evidence_need(state))
    classified_replay = apply_evidence_need_delta(classified, determine_evidence_need(classified))
    ready = apply_evidence_routing_delta(classified_replay, route_evidence(classified_replay))
    ready_replay = apply_evidence_routing_delta(ready, route_evidence(ready))

    assert classified_replay == classified
    assert ready_replay == ready
    assert [event.sequence for event in ready.trace_events] == [1, 2]
