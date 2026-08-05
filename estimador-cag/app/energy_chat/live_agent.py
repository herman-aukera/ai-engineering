"""Live-provider Energy Aware Chat orchestration for human MVP testing."""

from __future__ import annotations

from app.energy_chat.baseline import generate_deepseek_baseline_draft
from app.energy_chat.contracts import (
    DeepSeekBaselineRequest,
    DeepSeekBaselineResult,
    EnergyAwareChatAgentRequest,
    EnergyAwareChatAgentResult,
    EnergyChatRequest,
    ProjectRagChunk,
    ProjectRagRequest,
)
from app.energy_chat.evaluator import evaluate_with_one_pass_repair, run_evaluation
from app.energy_chat.rag import retrieve_project_context


def run_live_energy_aware_chat_agent(
    request: EnergyAwareChatAgentRequest,
    *,
    baseline_result: DeepSeekBaselineResult | None = None,
) -> EnergyAwareChatAgentResult:
    """
    Run the human-facing MVP path with a real provider draft.

    The deterministic `/energy-chat/chat` endpoint exists for CI-safe proof. This
    live path exists for manual product testing: retrieve project evidence, ask
    DeepSeek for a draft with the normal provider fallback ladder, then evaluate
    and repair the draft through the Energy Card.
    """

    rag = retrieve_project_context(
        ProjectRagRequest(
            query=request.user_message,
            mode=request.mode,
            k=request.k,
        )
    )
    baseline = baseline_result or generate_deepseek_baseline_draft(
        DeepSeekBaselineRequest(
            user_message=build_provider_grounded_prompt(request=request, chunks=rag.results),
            mode=request.mode,
            tier="flash",
            max_tokens=1200,
            required_constraints=request.required_constraints,
            required_sections=request.required_sections,
            metadata={
                "agent_path": "live_provider_retrieval_draft_critic_decider",
                "original_user_message": request.user_message,
                **request.metadata,
            },
        )
    )
    evaluation_request = EnergyChatRequest(
        user_message=request.user_message,
        draft_answer=baseline.draft_answer,
        mode=request.mode,
        required_constraints=request.required_constraints,
        required_sections=request.required_sections,
        evidence_refs=[*rag.evidence_refs, *baseline.evidence_refs],
        metadata={
            "agent_path": "live_provider_retrieval_draft_critic_decider",
            "retrieval_strategy": rag.retrieval_strategy,
            "provider": baseline.provider,
            "model": baseline.model,
            "tier": baseline.tier,
            "fallback_used": baseline.fallback_used,
            **request.metadata,
        },
    )
    evaluation = run_evaluation(evaluation_request)
    repair_evaluation = evaluate_with_one_pass_repair(evaluation_request)
    final_answer = repair_evaluation.final_result.request.draft_answer
    execution_audit = _build_execution_audit(
        request=request,
        baseline=baseline,
        evaluation_energy=evaluation.energy_card.energy,
        final_energy=repair_evaluation.final_result.energy_card.energy,
        repair_attempted=repair_evaluation.repair_attempted,
        retrieved_refs=rag.evidence_refs,
    )

    return EnergyAwareChatAgentResult(
        request=request,
        rag=rag,
        draft_answer=baseline.draft_answer,
        evaluation=evaluation,
        repair_evaluation=repair_evaluation,
        final_answer=final_answer,
        energy_card=repair_evaluation.final_result.energy_card,
        agent_trace=execution_audit["visible_steps"],
        metadata={
            "mvp_layer": "live_provider_rag_plus_agent_orchestration",
            "claim_boundary": "production_oriented_mvp_not_production_ready",
            "quality_claim": "measurement_only_no_quality_claim",
            "provider": baseline.provider,
            "model": baseline.model,
            "tier": baseline.tier,
            "fallback_used": baseline.fallback_used,
            "input_tokens": baseline.input_tokens,
            "output_tokens": baseline.output_tokens,
            "cost_usd": baseline.cost_usd,
            "finish_reason": baseline.finish_reason,
            **execution_audit,
        },
    )


def build_provider_grounded_prompt(
    *,
    request: EnergyAwareChatAgentRequest,
    chunks: list[ProjectRagChunk],
) -> str:
    evidence_block = "\n\n".join(
        f"[{chunk.evidence_ref}] {chunk.title}: {chunk.content}" for chunk in chunks
    ) or "No project evidence retrieved. State that evidence is missing if the answer depends on project facts."
    constraints = ", ".join(request.required_constraints) or "none supplied"
    sections = ", ".join(request.required_sections) or "none supplied"
    return (
        "You are the live draft provider for Energy Aware Chat. Answer the original user request.\n"
        "Use the retrieved project evidence when it is relevant. Do not invent citations or claim production readiness.\n"
        "Do not include hidden chain of thought. Be direct and useful.\n\n"
        f"Mode: {request.mode}\n"
        f"Required constraints: {constraints}\n"
        f"Required sections: {sections}\n\n"
        f"Retrieved project evidence:\n{evidence_block}\n\n"
        f"Original user request:\n{request.user_message}"
    )


def _build_execution_audit(
    *,
    request: EnergyAwareChatAgentRequest,
    baseline: DeepSeekBaselineResult,
    evaluation_energy: int,
    final_energy: int,
    repair_attempted: bool,
    retrieved_refs: list[str],
) -> dict[str, object]:
    """Return visible execution facts without exposing hidden model reasoning."""

    provider_call_count = 1
    deterministic_step_count = 4
    fallback_note = "fallback used" if baseline.fallback_used else "fallback available but not used"
    visible_steps = [
        f"1. mode_resolver: selected `{request.mode}` policy overlay from the UI selection.",
        (
            "2. retrieval_agent: ran deterministic project RAG and selected "
            f"{len(retrieved_refs)} evidence refs: {', '.join(retrieved_refs) or 'none'}."
        ),
        (
            "3. live_draft_agent: made 1 provider draft call through "
            f"{baseline.provider}/{baseline.model}; {fallback_note}."
        ),
        (
            "4. critic_agent: ran deterministic critics against required constraints, "
            "required sections, evidence refs, structure, safety, and scope."
        ),
        (
            "5. decider_agent: compared energy to policy thresholds and chose "
            f"final energy {final_energy} after initial energy {evaluation_energy}."
        ),
        (
            "6. repair_agent: "
            + ("applied one deterministic repair pass." if repair_attempted else "did not run because repair was not required.")
        ),
    ]
    return {
        "call_plan": {
            "provider_draft_calls": provider_call_count,
            "deterministic_steps": deterministic_step_count,
            "critic_llm_calls": 0,
            "repair_llm_calls": 0,
            "fallback_ladder": ["deepseek:flash", "deepseek:pro", "kimi:backup", "kimi:backup_pro"],
            "note": (
                "This MVP does not execute six LLM calls per question. It uses one live provider draft call, "
                "then deterministic RAG, critics, scoring, decider, and optional deterministic repair."
            ),
        },
        "visible_steps": visible_steps,
        "reasoning_visibility": (
            "The UI shows a reasoning summary and execution audit. It does not expose hidden chain-of-thought."
        ),
        "energy_delta": final_energy - evaluation_energy,
    }
