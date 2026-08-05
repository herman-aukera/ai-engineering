from app.energy_chat.candidate_provider import (
    CandidateGenerationResult,
    CandidateProviderRequest,
)
from app.energy_chat.contracts import EnergyChatRequest
from app.energy_chat.evaluator import evaluate_with_one_pass_repair
from app.energy_chat.graph_runtime import run_energy_chat_graph
from app.energy_chat.graph_state import (
    CostBudget,
    EnergyChatGraphState,
    ProviderMetrics,
    RetryBudget,
)
from app.energy_chat.repair_nodes import RepairProposal


class RepairableProvider:
    def __init__(self, *, cost_usd: float = 0.01) -> None:
        self.calls = 0
        self.cost_usd = cost_usd

    def generate(self, request: CandidateProviderRequest) -> CandidateGenerationResult:
        self.calls += 1
        return CandidateGenerationResult(
            answer="Start with tests.",
            evidence_refs=request.evidence_refs,
            metrics=ProviderMetrics(
                provider_call_id=request.provider_call_id,
                provider="fake",
                model="repairable-v1",
                tier="local",
                input_tokens=10,
                output_tokens=4,
                cost_usd=self.cost_usd,
                latency_ms=1,
            ),
        )


def _initial(*, retries: int = 1) -> EnergyChatGraphState:
    return EnergyChatGraphState(
        thread_id="thread-1",
        request_id="request-1",
        trace_id="trace-1",
        user_request="Review this release-readiness answer",
        mode="chat_lite",
        policy_version="unresolved",
        constraints=["DeepSeek remains deferred"],
        retry_budget=RetryBudget(max_attempts=retries),
        cost_budget=CostBudget(limit_usd=0.02),
    )


def test_graph_one_pass_repair_matches_existing_deterministic_repair() -> None:
    provider = RepairableProvider()
    legacy = evaluate_with_one_pass_repair(
        EnergyChatRequest(
            user_message="Review this release-readiness answer",
            draft_answer="Start with tests.",
            required_constraints=["DeepSeek remains deferred"],
        )
    )

    state = run_energy_chat_graph(_initial(), provider=provider)

    assert provider.calls == 1
    assert len(state.candidate_versions) == 2
    assert state.candidate_versions[-1].answer == legacy.final_result.request.draft_answer
    assert state.decision_outcomes[0].disposition == "repair"
    assert state.decision_outcomes[-1].disposition == legacy.final_result.decision.decision
    assert state.retry_budget.attempts_used == 1
    assert state.cost_budget.spent_usd == 0.01
    assert len(state.repair_requests) == 1
    assert state.repair_results[-1].outcome == "improved"
    assert state.status == "evaluated"


def test_zero_retry_budget_terminates_without_creating_candidate_version_two() -> None:
    provider = RepairableProvider()

    state = run_energy_chat_graph(_initial(retries=0), provider=provider)

    assert provider.calls == 1
    assert len(state.candidate_versions) == 1
    assert state.decision_outcomes[-1].disposition == "escalate"
    assert state.decision_outcomes[-1].policy_rule_id == "repair_budget_exhausted"
    assert state.repair_requests == []
    assert state.repair_results == []
    assert state.status == "evaluated"


def test_non_improving_repair_terminates_after_one_full_reevaluation() -> None:
    class NonImprovingStrategy:
        def propose(self, request, evaluation) -> RepairProposal:
            return RepairProposal(
                proposed_answer=request.draft_answer,
                instructions=["intentionally unchanged test proposal"],
                repairs_applied=["no_change"],
            )

    state = run_energy_chat_graph(
        _initial(),
        provider=RepairableProvider(cost_usd=0.0),
        repair_strategy=NonImprovingStrategy(),
    )

    assert len(state.candidate_versions) == 2
    assert len(state.energy_scores) == 2
    assert state.energy_scores[-1].score.total_energy == state.energy_scores[0].score.total_energy
    assert state.repair_results[-1].outcome == "no_improvement"
    assert state.retry_budget.attempts_used == 1


def test_repaired_graph_replay_does_not_repeat_calls_or_history() -> None:
    provider = RepairableProvider(cost_usd=0.0)
    first = run_energy_chat_graph(_initial(), provider=provider)
    replayed = run_energy_chat_graph(first, provider=provider)

    assert provider.calls == 1
    assert replayed == first
