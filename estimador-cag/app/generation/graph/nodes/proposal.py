"""Deterministic proposal node — generates a structured estimate proposal."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.generation.graph.review_state import ReviewedEstimationGraphState

NODE_NAME = "proposal"

ProposalNode = Callable[
    [ReviewedEstimationGraphState],
    Awaitable[ReviewedEstimationGraphState],
]


def build_proposal_node() -> ProposalNode:
    """Synthesize a structured proposal from the validated estimation state."""

    async def proposal(
        state: ReviewedEstimationGraphState,
    ) -> ReviewedEstimationGraphState:
        estimate = state.get("estimate") or {}
        reliability = state.get("reliability_report") or {}
        critic = state.get("critic_report") or {}
        boss = state.get("boss_decision") or {}
        arb = state.get("arbitrated_assessment") or {}

        proposal_dict: dict[str, object] = {
            "total_hours": estimate.get("total_hours"),
            "total_cost_eur": estimate.get("total_cost_eur"),
            "currency": estimate.get("currency", "EUR"),
            "reliability_score": reliability.get("overall_score"),
            "critic_verdict": critic.get("verdict"),
            "boss_action": boss.get("action"),
            "complexity": arb.get("arbitrated_level"),
            "human_review_required": (
                reliability.get("requires_human_review", False)
                or arb.get("human_review_required", False)
            ),
            "component_count": len(estimate.get("components", [])),
            "recommendations": _recommendations(reliability, critic, boss),
        }

        return {
            "proposal": proposal_dict,
            "trace_events": [
                {
                    "event_type": "proposal_generated",
                    "node": NODE_NAME,
                    "summary": (
                        f"Proposal: {proposal_dict.get('total_hours')}h, "
                        f"reliability {proposal_dict.get('reliability_score')}, "
                        f"boss {proposal_dict.get('boss_action')}"
                    ),
                    "evidence_refs": [],
                    "state_delta_keys": ["proposal", "trace_events"],
                }
            ],
        }

    return proposal


def _recommendations(
    reliability: dict[str, object],
    critic: dict[str, object],
    boss: dict[str, object],
) -> list[str]:
    recs: list[str] = []
    if float(reliability.get("overall_score", 1) or 1) < 0.6:
        recs.append("Increase evidence coverage before accepting this estimate.")
    if critic.get("verdict") == "needs_iteration":
        recs.append("Address Critic findings and re-run estimation.")
    if boss.get("action") == "human_review":
        recs.append("Human review required before this estimate can be accepted.")
    if not recs:
        recs.append("Estimate is ready for acceptance. No blockers.")
    return recs
