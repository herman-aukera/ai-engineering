"""Integration proof for graph observability and evidence integrity."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.energy_chat.candidate_provider import (
    CandidateGenerationResult,
    CandidateProviderRequest,
)
from app.energy_chat.evidence_hardening import metadata_without_body
from app.energy_chat.graph_checkpoint import InMemoryCheckpointer
from app.energy_chat.graph_runtime import run_energy_chat_graph
from app.energy_chat.graph_state import EnergyChatGraphState, ProviderMetrics
from app.energy_chat.runtime_container import EnergyChatApplicationRuntime
from app.main import app

client = TestClient(app)


class FabricatedCitationProvider:
    def generate(self, request: CandidateProviderRequest) -> CandidateGenerationResult:
        return CandidateGenerationResult(
            answer=(
                "The architecture is fully production ready according to "
                "[source:made_up_evidence]. The design uses deterministic policy, "
                "bounded repair, and an audit ledger. Next action: deploy immediately."
            ),
            evidence_refs=request.evidence_refs,
            metrics=ProviderMetrics(
                provider_call_id=request.provider_call_id,
                provider="fake",
                model="fabricated-citation-fixture",
                tier="test",
            ),
        )


class KnownCitationProvider:
    def generate(self, request: CandidateProviderRequest) -> CandidateGenerationResult:
        citation = request.evidence_refs[0]
        return CandidateGenerationResult(
            answer=(
                f"The project architecture is grounded in [{citation}]. It separates "
                "candidate generation from deterministic critics, scoring, decisions, "
                "and audit projection. Next action: review the linked project source."
            ),
            evidence_refs=request.evidence_refs,
            metrics=ProviderMetrics(
                provider_call_id=request.provider_call_id,
                provider="fake",
                model="known-citation-fixture",
                tier="test",
            ),
        )


def _project_state(trace_id: str) -> EnergyChatGraphState:
    return EnergyChatGraphState(
        thread_id=f"thread-{trace_id}",
        request_id=f"request-{trace_id}",
        trace_id=trace_id,
        user_request="Explain the Energy Aware Chat architecture from project sources.",
        mode="project",
        policy_version="unresolved",
    )


def test_v2_response_contains_actual_node_spans_and_safe_metrics() -> None:
    previous = app.state.energy_chat_runtime
    app.state.energy_chat_runtime = EnergyChatApplicationRuntime()
    try:
        response = client.post(
            "/energy-chat/v2/chat",
            json={
                "user_message": "Explain the Energy Aware Chat architecture.",
                "thread_id": "thread-integrated-spans",
            },
        )
    finally:
        app.state.energy_chat_runtime = previous

    assert response.status_code == 200, response.text
    body = response.json()
    metrics = body["graph_metrics"]
    assert metrics["node_count"] >= 8
    assert metrics["failed_node_count"] == 0
    assert metrics["provider_call_count"] == 1
    assert any(
        span["node_name"] == "generate_candidate"
        for span in metrics["node_spans"]
    )
    assert all(span["duration_ms"] >= 0 for span in metrics["node_spans"])
    assert "payload" not in metrics["safe_trace_summary"][0]
    assert "graph_node_spans_recorded" in body["execution_markers"]


def test_project_evidence_hashes_flow_into_ledger_without_bodies() -> None:
    result = run_energy_chat_graph(
        _project_state("trace-integrity-ledger"),
        provider=KnownCitationProvider(),
    )

    assert result.evidence_body_metadata
    hashed = [
        item
        for item in result.evidence_body_metadata
        if item.body_hash_status == "hashed"
    ]
    assert hashed
    assert all(item.body_hash and item.body_hash.startswith("sha256:") for item in hashed)
    assert all(item.verification_status == "verified" for item in hashed)
    assert all(item.freshness_status == "not_applicable" for item in hashed)
    assert "content" not in hashed[0].model_dump()

    ledger = result.decision_ledger_entries[-1]
    ledger_by_ref = {item.evidence_ref: item for item in ledger.evidence_integrity}
    for metadata in hashed:
        projected = ledger_by_ref[metadata.evidence_ref]
        assert projected.body_hash == metadata.body_hash
        assert projected.verification_status == "verified"
        assert projected.body_included is False


def test_known_citation_is_validated_without_fabrication_finding() -> None:
    result = run_energy_chat_graph(
        _project_state("trace-known-citation"),
        provider=KnownCitationProvider(),
    )

    validation = result.citation_validations[-1]
    assert validation.validation.valid_citations
    assert validation.validation.unknown_citations == []
    assert validation.validation.has_fabricated_citations is False
    assert "fabricated_citation" not in {
        finding.violation_id for finding in result.critic_findings
    }


def test_fabricated_citation_causes_hard_reject_and_safe_projection() -> None:
    result = run_energy_chat_graph(
        _project_state("trace-fabricated-citation"),
        provider=FabricatedCitationProvider(),
    )

    validation = result.citation_validations[-1]
    assert validation.validation.unknown_citations == ["source:made_up_evidence"]
    assert validation.validation.has_fabricated_citations is True
    assert "fabricated_citation" in {
        finding.violation_id for finding in result.critic_findings
    }
    assert result.decision_outcomes[-1].disposition == "reject"
    assert "source:made_up_evidence" not in (result.final_answer or "")
    assert any(
        "not present in the evidence allow-list" in limitation
        for limitation in result.decision_ledger_entries[-1].limitations
    )


def test_checkpoint_replay_preserves_spans_without_duplicate_execution() -> None:
    checkpointer = InMemoryCheckpointer()
    state = _project_state("trace-span-replay")
    first = run_energy_chat_graph(
        state,
        provider=KnownCitationProvider(),
        checkpointer=checkpointer.langgraph_saver,
    )
    replay = run_energy_chat_graph(
        first,
        provider=KnownCitationProvider(),
        checkpointer=checkpointer.langgraph_saver,
    )

    assert replay.node_spans == first.node_spans
    assert replay.citation_validations == first.citation_validations
    assert replay.evidence_body_metadata == first.evidence_body_metadata


def test_sensitive_or_unavailable_body_is_not_hashed() -> None:
    metadata = metadata_without_body(
        "web:restricted_source",
        permitted=False,
        freshness_status="unknown",
    )
    assert metadata.body_hash is None
    assert metadata.body_hash_status == "not_permitted"
    assert metadata.byte_count is None
    assert "body" not in metadata.model_dump()
