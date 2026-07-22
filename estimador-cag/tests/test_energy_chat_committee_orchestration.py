"""Bounded committee generation and adaptive-routing contracts."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.energy_chat.candidate_provider import CandidateProviderRequest
from app.energy_chat.committee_orchestration import (
    CommitteeCandidateProvider,
    build_committee_selection,
    resolve_adaptive_orchestration,
)
from app.energy_chat.runtime_container import EnergyChatApplicationRuntime
from app.main import app

client = TestClient(app)


def _request() -> CandidateProviderRequest:
    return CandidateProviderRequest(
        provider_call_id="committee-provider-call",
        user_request="Prepare a production release recommendation with explicit evidence limits.",
        mode="project",
        constraints=["do not claim unverified deployment", "preserve rollback"],
        required_sections=["Decision", "Evidence", "Limitations"],
        evidence_refs=["source:release-policy"],
    )


def test_committee_generates_three_distinct_independently_scored_proposals() -> None:
    selection = build_committee_selection(_request())

    assert [item.role for item in selection.proposals] == [
        "grounded",
        "constraint_first",
        "skeptical",
    ]
    assert len({item.answer for item in selection.proposals}) == 3
    assert all(item.total_energy >= 0 for item in selection.proposals)
    selected = next(
        item
        for item in selection.proposals
        if item.proposal_id == selection.selected_proposal_id
    )
    assert selected.role == selection.selected_role
    assert selected.hard_reject_count == min(
        item.hard_reject_count for item in selection.proposals
    )
    assert "deterministic Boss" in selection.selection_reason


def test_committee_provider_is_keyless_bounded_and_observable() -> None:
    provider = CommitteeCandidateProvider()
    result = provider.generate(_request())

    assert provider.last_selection is not None
    assert len(provider.last_selection.proposals) == 3
    assert result.metrics.provider_call_id == "committee-provider-call"
    assert result.metrics.provider == "deterministic_committee"
    assert result.metrics.model.startswith("energy-chat-committee-v1:")
    assert result.metrics.cost_usd == 0.0
    assert result.metrics.fallback_used is False
    assert result.metrics.finish_reason is not None
    assert "proposals:3" in result.metrics.finish_reason


def test_adaptive_router_escalates_only_on_explicit_signals() -> None:
    ordinary = resolve_adaptive_orchestration(
        user_request="Explain the current graph structure.",
        mode="project",
        constraints=[],
        required_sections=[],
    )
    risky = resolve_adaptive_orchestration(
        user_request="Approve this production release using the latest evidence.",
        mode="research",
        constraints=["cite evidence", "preserve rollback"],
        required_sections=["Decision", "Evidence", "Risk"],
    )

    assert ordinary.resolved_mode == "committee"
    assert "high_risk_domain_marker" in ordinary.reason_codes
    assert risky.resolved_mode == "committee"
    assert "research_evidence_risk" in risky.reason_codes
    assert "multiple_hard_constraints" in risky.reason_codes


def test_adaptive_router_keeps_ordinary_low_risk_request_on_critic() -> None:
    decision = resolve_adaptive_orchestration(
        user_request="Explain how reducers work.",
        mode="project",
        constraints=[],
        required_sections=[],
    )

    assert decision.resolved_mode == "critic"
    assert decision.reason_codes == ["ordinary_request"]


def test_deterministic_committee_route_is_exposed_by_v2_api() -> None:
    previous = app.state.energy_chat_runtime
    app.state.energy_chat_runtime = EnergyChatApplicationRuntime()
    try:
        response = client.post(
            "/energy-chat/v2/chat",
            json={
                "user_message": "Prepare a production release recommendation.",
                "orchestration_mode": "committee",
            },
        )
    finally:
        app.state.energy_chat_runtime = previous

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["requested_orchestration_mode"] == "committee"
    assert body["resolved_orchestration_mode"] == "committee"
    assert body["orchestration_candidate_count"] == 3
    assert body["served_provider"] == "deterministic_committee"
    assert body["provider_metrics_summary"]["provider_call_count"] == 1
    assert body["provider_metrics_summary"]["total_cost_usd"] == 0.0


def test_adaptive_api_routes_low_risk_to_critic_and_high_risk_to_committee() -> None:
    previous = app.state.energy_chat_runtime
    app.state.energy_chat_runtime = EnergyChatApplicationRuntime()
    try:
        ordinary = client.post(
            "/energy-chat/v2/chat",
            json={
                "user_message": "Explain how reducers work.",
                "orchestration_mode": "adaptive",
            },
        )
        risky = client.post(
            "/energy-chat/v2/chat",
            json={
                "user_message": "Approve this production release using the latest evidence.",
                "orchestration_mode": "adaptive",
            },
        )
    finally:
        app.state.energy_chat_runtime = previous

    assert ordinary.status_code == 200, ordinary.text
    assert risky.status_code == 200, risky.text
    assert ordinary.json()["resolved_orchestration_mode"] == "critic"
    assert ordinary.json()["orchestration_candidate_count"] == 1
    assert risky.json()["resolved_orchestration_mode"] == "committee"
    assert risky.json()["orchestration_candidate_count"] == 3


def test_live_committee_and_adaptive_are_rejected_until_calibrated() -> None:
    committee = client.post(
        "/energy-chat/v2/chat/live",
        json={
            "user_message": "test live committee",
            "execution_profile": "live_bounded",
            "orchestration_mode": "committee",
        },
    )
    adaptive = client.post(
        "/energy-chat/v2/chat/live",
        json={
            "user_message": "test live adaptive",
            "execution_profile": "live_bounded",
            "orchestration_mode": "adaptive",
        },
    )

    assert committee.status_code == 400
    assert committee.json()["detail"]["error"] == "unsupported_orchestration_mode"
    assert adaptive.status_code == 400
    assert adaptive.json()["detail"]["error"] == "unsupported_orchestration_mode"
