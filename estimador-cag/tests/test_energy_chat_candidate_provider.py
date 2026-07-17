import pytest

from app.energy_chat.agent import build_project_grounded_draft
from app.energy_chat.candidate_node import apply_candidate_delta, generate_candidate
from app.energy_chat.candidate_provider import (
    BaselineCandidateProvider,
    CandidateGenerationResult,
    CandidateProviderRequest,
    DeterministicCandidateProvider,
    ProviderBudget,
    ProviderBudgetExceededError,
    ProviderMetrics,
)
from app.energy_chat.contracts import EnergyAwareChatAgentRequest, ProjectRagRequest
from app.energy_chat.graph_state import CostBudget, EnergyChatGraphState
from app.energy_chat.rag import retrieve_project_context


def _state() -> EnergyChatGraphState:
    rag = retrieve_project_context(
        ProjectRagRequest(query="Is deployment evidence required?", mode="project", k=2)
    )
    return EnergyChatGraphState(
        thread_id="thread-1",
        request_id="request-1",
        trace_id="trace-1",
        user_request="Is deployment evidence required?",
        mode="project",
        policy_version="1.0.0",
        constraints=["deployment evidence"],
        evidence_refs=rag.evidence_refs,
        project_rag=rag,
        status="evidence_ready",
    )


def test_deterministic_provider_preserves_existing_local_draft_behavior() -> None:
    state = _state()
    provider = DeterministicCandidateProvider()

    delta = generate_candidate(state, provider=provider)
    expected = build_project_grounded_draft(
        request=EnergyAwareChatAgentRequest(
            user_message=state.user_request,
            mode=state.mode,
            required_constraints=state.constraints,
        ),
        evidence_refs=state.evidence_refs,
    )

    assert delta.candidate_versions[0].answer == expected
    assert delta.provider_metrics[0].provider == "deterministic_local"
    assert (
        delta.candidate_versions[0].provider_call_id
        == delta.provider_metrics[0].provider_call_id
    )
    assert delta.provider_metrics[0].cost_usd == 0.0
    assert delta.provider_metrics[0].latency_ms == 0
    assert delta.status == "candidate_ready"


def test_candidate_node_replay_does_not_repeat_provider_call() -> None:
    class CountingProvider:
        def __init__(self) -> None:
            self.calls = 0

        def generate(self, request: CandidateProviderRequest) -> CandidateGenerationResult:
            self.calls += 1
            return CandidateGenerationResult(
                answer="Decision: retain evidence. Next action: validate the checkpoint.",
                evidence_refs=request.evidence_refs,
                metrics=ProviderMetrics(
                    provider_call_id=request.provider_call_id,
                    provider="fake",
                    model="fake-v1",
                    tier="local",
                    input_tokens=10,
                    output_tokens=12,
                    cost_usd=0.0,
                    latency_ms=1,
                ),
            )

    provider = CountingProvider()
    first = apply_candidate_delta(_state(), generate_candidate(_state(), provider=provider))
    replayed = apply_candidate_delta(first, generate_candidate(first, provider=provider))

    assert replayed == first
    assert provider.calls == 1


def test_candidate_node_enforces_cost_budget_before_state_application() -> None:
    class ExpensiveProvider:
        def generate(self, request: CandidateProviderRequest) -> CandidateGenerationResult:
            return CandidateGenerationResult(
                answer="Decision: candidate. Next action: stop.",
                metrics=ProviderMetrics(
                    provider_call_id=request.provider_call_id,
                    provider="fake",
                    model="expensive",
                    tier="pro",
                    cost_usd=2.0,
                    latency_ms=1,
                ),
            )

    with pytest.raises(ProviderBudgetExceededError, match="cost"):
        generate_candidate(
            _state(),
            provider=ExpensiveProvider(),
            budget=ProviderBudget(max_cost_usd=0.01),
        )


def test_candidate_node_enforces_cumulative_graph_cost_budget() -> None:
    class CumulativeProvider:
        def generate(self, request: CandidateProviderRequest) -> CandidateGenerationResult:
            return CandidateGenerationResult(
                answer="Decision: candidate. Next action: stop.",
                metrics=ProviderMetrics(
                    provider_call_id=request.provider_call_id,
                    provider="fake",
                    model="cumulative",
                    tier="local",
                    cost_usd=0.02,
                    latency_ms=1,
                ),
            )

    state = _state().model_copy(update={"cost_budget": CostBudget(limit_usd=0.01)})
    with pytest.raises(ProviderBudgetExceededError, match="Cumulative"):
        generate_candidate(
            state,
            provider=CumulativeProvider(),
            budget=ProviderBudget(max_cost_usd=0.05),
        )


@pytest.mark.parametrize(
    ("metric_update", "budget", "message"),
    [
        ({"output_tokens": 101}, ProviderBudget(max_output_tokens=100), "token"),
        ({"latency_ms": 101}, ProviderBudget(max_latency_ms=100), "latency"),
        ({"retries": 2}, ProviderBudget(max_retries=1), "retry"),
    ],
)
def test_provider_budget_enforces_tokens_latency_and_retries(
    metric_update: dict[str, int], budget: ProviderBudget, message: str
) -> None:
    class OverBudgetProvider:
        def generate(self, request: CandidateProviderRequest) -> CandidateGenerationResult:
            metrics = ProviderMetrics(
                provider_call_id=request.provider_call_id,
                provider="fake",
                model="over-budget",
                tier="local",
                **metric_update,
            )
            return CandidateGenerationResult(answer="Visible answer", metrics=metrics)

    with pytest.raises(ProviderBudgetExceededError, match=message):
        generate_candidate(_state(), provider=OverBudgetProvider(), budget=budget)


def test_candidate_node_rejects_whitespace_only_output() -> None:
    class EmptyProvider:
        def generate(self, request: CandidateProviderRequest):
            return {
                "answer": "   ",
                "metrics": {
                    "provider_call_id": request.provider_call_id,
                    "provider": "fake",
                    "model": "empty",
                    "tier": "local",
                    "cost_usd": 0.0,
                    "latency_ms": 0,
                },
            }

    with pytest.raises(ValueError):
        generate_candidate(_state(), provider=EmptyProvider())


def test_baseline_adapter_maps_existing_fallback_result_and_latency() -> None:
    class ExistingProvider:
        def complete_with_fallback_messages(self, **kwargs):
            return {
                "estimation": "Decision: use fallback. Next action: validate it.",
                "provider": "kimi",
                "model": "kimi-test",
                "tier": "backup",
                "input_tokens": 20,
                "output_tokens": 9,
                "cost_usd": 0.002,
                "finish_reason": "stop",
                "fallback_used": True,
            }

    ticks = iter([10.0, 10.125])
    adapter = BaselineCandidateProvider(provider=ExistingProvider(), clock=lambda: next(ticks))
    request = CandidateProviderRequest(
        provider_call_id="call-1",
        user_request="Draft an answer.",
        mode="project",
        max_tokens=100,
    )

    result = adapter.generate(request)

    assert result.metrics.provider_call_id == "call-1"
    assert result.metrics.provider == "kimi"
    assert result.metrics.tier == "backup"
    assert result.metrics.fallback_used is True
    assert result.metrics.latency_ms == 125
    assert result.answer.startswith("Decision:")
