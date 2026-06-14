from __future__ import annotations

from app.energy_chat.agent import run_energy_aware_chat_agent
from app.energy_chat.contracts import EnergyAwareChatAgentRequest


def test_energy_chat_agent_returns_grounded_energy_card() -> None:
    result = run_energy_aware_chat_agent(
        EnergyAwareChatAgentRequest(
            user_message="Can this project skip deployment and still be final-project ready?",
            required_constraints=["deployment evidence"],
            required_sections=["Decision", "Next action"],
        )
    )

    assert result.rag.results
    assert result.rag.evidence_refs
    assert result.final_answer
    assert result.energy_card.decision == "accept"
    assert result.energy_card.hard_constraints_passed is True
    assert "retrieval_agent" in result.agent_trace[0]
    assert result.metadata["mvp_layer"] == "rag_plus_agent_orchestration"
    assert result.metadata["quality_claim"] == "measurement_only_no_quality_claim"
    assert "deployment evidence" in result.final_answer


def test_energy_chat_agent_preserves_rag_evidence_in_evaluation() -> None:
    result = run_energy_aware_chat_agent(
        EnergyAwareChatAgentRequest(
            user_message="How should DeepSeek fallback to Kimi be handled?",
            k=2,
        )
    )

    assert result.evaluation.request.evidence_refs == result.rag.evidence_refs
    assert result.repair_evaluation.final_result.request.evidence_refs == result.rag.evidence_refs
    assert any(chunk.source_id == "provider_fallback" for chunk in result.rag.results)
