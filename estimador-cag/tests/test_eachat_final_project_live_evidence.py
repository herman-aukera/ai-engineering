from __future__ import annotations

from app.energy_chat.candidate_provider import BaselineCandidateProvider, CandidateProviderRequest
from app.energy_chat.contracts import ProjectRagChunk, ProjectRagResult


class FakeLiveBaselineProvider:
    def complete_messages(self, **kwargs):
        return {
            "estimation": (
                "Check the retrieved PostgreSQL connection evidence before assigning a root "
                "cause. Next action: compare active sessions with the configured limit."
            ),
            "provider": "deepseek",
            "model": "fake-live-model",
            "tier": "flash",
            "input_tokens": 20,
            "output_tokens": 16,
            "cost_usd": 0.001,
            "finish_reason": "stop",
            "fallback_used": False,
        }


def test_live_candidate_preserves_real_rag_refs_alongside_provider_evidence() -> None:
    rag = ProjectRagResult(
        query="Which PostgreSQL connection evidence should I inspect?",
        k=1,
        retrieval_strategy="openai_embedding_postgres_exact_cosine_support_rag",
        results=[
            ProjectRagChunk(
                source_id="postgres_connections",
                title="PostgreSQL connections",
                content="Connection limits constrain concurrent sessions.",
                evidence_ref="source:postgres_connections:chunk-1",
                score=0.91,
            )
        ],
        evidence_refs=["source:postgres_connections:chunk-1"],
        grounding_summary="Retrieved one persisted support chunk.",
    )
    adapter = BaselineCandidateProvider(provider=FakeLiveBaselineProvider())
    adapter.configure_fallback_policy(
        allow_provider_fallback=False,
        tier_ladder=["flash"],
    )

    result = adapter.generate(
        CandidateProviderRequest(
            provider_call_id="call-final-project-live",
            user_request="Which PostgreSQL connection evidence should I inspect?",
            mode="project",
            evidence_refs=rag.evidence_refs,
            project_rag=rag,
            max_tokens=256,
        )
    )

    assert "source:postgres_connections:chunk-1" in result.evidence_refs
    assert "provider:deepseek_baseline" in result.evidence_refs
    assert "tier:flash" in result.evidence_refs
    assert result.metrics.fallback_used is False
