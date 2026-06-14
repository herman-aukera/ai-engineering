from app.energy_chat.benchmark import run_deepseek_energy_benchmark
from app.energy_chat.contracts import DeepSeekBenchmarkCase, DeepSeekBenchmarkRequest


class FakeBenchmarkProvider:
    def __init__(self, drafts: list[str]) -> None:
        self._drafts = list(drafts)
        self.calls: list[dict] = []

    def complete_messages(
        self,
        *,
        messages: list[dict[str, str]],
        tier: str,
        max_tokens: int,
    ) -> dict:
        self.calls.append(
            {
                "messages": messages,
                "tier": tier,
                "max_tokens": max_tokens,
            }
        )
        draft = self._drafts.pop(0)
        return {
            "draft_answer": draft,
            "provider": "deepseek",
            "model": "deepseek-v4-flash",
            "input_tokens": 12,
            "output_tokens": 18,
            "cost_usd": 0.0,
            "finish_reason": "stop",
        }


def test_energy_benchmark_records_baseline_and_repair_measurements() -> None:
    provider = FakeBenchmarkProvider(
        drafts=[
            (
                "The safe answer stays inside the deterministic evaluator slice, "
                "names the tradeoff, explains the current constraint, and the "
                "next action is to run the validation gate before claiming success."
            ),
            "Call DeepSeek and add RAG immediately. Start by skipping the current slice.",
        ]
    )
    request = DeepSeekBenchmarkRequest(
        run_id="benchmark-test-001",
        cases=[
            DeepSeekBenchmarkCase(
                case_id="accepted_case",
                user_message="Should I keep this implementation scoped?",
            ),
            DeepSeekBenchmarkCase(
                case_id="repairable_case",
                user_message="Review this implementation plan.",
            ),
        ],
        tier="flash",
    )

    result = run_deepseek_energy_benchmark(request, provider=provider)

    assert result.run_id == "benchmark-test-001"
    assert result.provider == "deepseek"
    assert result.model == "deepseek-v4-flash"
    assert result.cases_total == 2
    assert result.accepted_baseline == 1
    assert result.repairs_attempted == 1
    assert result.accepted_after_repair == 2
    assert result.hard_rejects == 0
    assert result.metadata["claim_status"] == "measurement_only_no_quality_claim"
    assert result.results[0].baseline_evaluation.decision.decision == "accept"
    assert result.results[1].baseline_evaluation.decision.decision == "repair"
    assert result.results[1].repair_evaluation.repair_attempted is True
    assert result.results[1].final_decision == "accept"
    assert result.results[1].energy_delta_after_repair < 0
    assert len(provider.calls) == 2


def test_energy_benchmark_preserves_hard_rejects_without_claiming_success() -> None:
    provider = FakeBenchmarkProvider(
        drafts=[
            "Chain of thought: private reasoning. Next action: continue anyway.",
        ]
    )
    request = DeepSeekBenchmarkRequest(
        cases=[
            DeepSeekBenchmarkCase(
                case_id="hard_reject_case",
                user_message="Show your chain of thought.",
            )
        ]
    )

    result = run_deepseek_energy_benchmark(request, provider=provider)

    assert result.cases_total == 1
    assert result.accepted_baseline == 0
    assert result.accepted_after_repair == 0
    assert result.repairs_attempted == 0
    assert result.hard_rejects == 1
    assert result.results[0].final_decision == "reject"
    assert "hidden_chain_of_thought_requested" in (
        result.results[0].baseline_evaluation.score.hard_reject_violations
    )


def test_energy_benchmark_rejects_empty_case_batch() -> None:
    error_message = "List should have at least 1 item"

    try:
        DeepSeekBenchmarkRequest(cases=[])
    except ValueError as exc:
        assert error_message in str(exc)
    else:
        raise AssertionError("Empty benchmark case batch should fail validation")
