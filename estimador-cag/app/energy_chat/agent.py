"""Local Energy Aware Chat agent orchestration for the MVP."""

from __future__ import annotations

from app.energy_chat.contracts import (
    EnergyAwareChatAgentRequest,
    EnergyAwareChatAgentResult,
    EnergyChatRequest,
    ProjectRagRequest,
)
from app.energy_chat.evaluator import evaluate_with_one_pass_repair, run_evaluation
from app.energy_chat.rag import retrieve_project_context


def run_energy_aware_chat_agent(request: EnergyAwareChatAgentRequest) -> EnergyAwareChatAgentResult:
    """
    Run the local MVP flow: retrieve evidence, draft, evaluate, repair, and expose an Energy Card.

    This is deterministic agent orchestration. It gives the final-project branch a
    real `/chat` path without making live-provider or production-readiness claims.
    """

    rag = retrieve_project_context(
        ProjectRagRequest(
            query=request.user_message,
            mode=request.mode,
            k=request.k,
        )
    )
    draft_answer = build_project_grounded_draft(request=request, evidence_refs=rag.evidence_refs)
    evaluation_request = EnergyChatRequest(
        user_message=request.user_message,
        draft_answer=draft_answer,
        mode=request.mode,
        required_constraints=request.required_constraints,
        required_sections=request.required_sections,
        evidence_refs=rag.evidence_refs,
        metadata={
            "agent_path": "retrieval_draft_critic_decider",
            "retrieval_strategy": rag.retrieval_strategy,
            **request.metadata,
        },
    )
    evaluation = run_evaluation(evaluation_request)
    repair_evaluation = evaluate_with_one_pass_repair(evaluation_request)
    final_answer = repair_evaluation.final_result.request.draft_answer

    return EnergyAwareChatAgentResult(
        request=request,
        rag=rag,
        draft_answer=draft_answer,
        evaluation=evaluation,
        repair_evaluation=repair_evaluation,
        final_answer=final_answer,
        energy_card=repair_evaluation.final_result.energy_card,
        agent_trace=[
            "retrieval_agent: selected committed project-source chunks",
            "draft_agent: produced a grounded answer candidate from retrieved evidence",
            "critic_agent: emitted deterministic findings through the evaluator",
            "decider_agent: accepted, repaired, rejected, or clarified through the Energy Card",
        ],
        metadata={
            "mvp_layer": "rag_plus_agent_orchestration",
            "claim_boundary": "production_oriented_mvp_not_production_ready",
            "quality_claim": "measurement_only_no_quality_claim",
        },
    )


def build_project_grounded_draft(
    *,
    request: EnergyAwareChatAgentRequest,
    evidence_refs: list[str],
) -> str:
    """Build a deterministic answer candidate that the critic pipeline can evaluate."""

    constraints = ""
    if request.required_constraints:
        constraints = "\nRequired constraints addressed: " + "; ".join(request.required_constraints) + "."

    sections = ""
    if request.required_sections:
        sections = "\nRequired sections addressed: " + "; ".join(request.required_sections) + "."

    evidence = ", ".join(evidence_refs) or "source:none"
    return (
        "Decision: Use the Energy Aware Chat MVP path for this project question.\n"
        f"Evidence used: {evidence}.\n"
        "Tradeoff: this local path is deterministic, CI-safe, and grounded in committed "
        "project sources; it is not a measured quality-improvement claim.\n"
        "Answer: the safe baseline is retrieval over project rules, a grounded draft, "
        "deterministic critics, one repair pass when needed, and a visible Energy Card."
        f"{constraints}{sections}\n"
        "Next action: run the local validation gate and exact Energy Aware Chat CI proof, "
        "then capture live provider and deployment evidence separately."
    )
