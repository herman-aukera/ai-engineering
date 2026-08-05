from app.energy_chat.benchmark import run_deepseek_energy_benchmark
from app.energy_chat.contracts import DeepSeekBenchmarkCase, DeepSeekBenchmarkRequest
from app.energy_chat.deepseek_quality_claim import (
    QUALITY_METRIC_NAME,
    build_deepseek_quality_evidence,
    render_deepseek_quality_markdown,
)
from app.energy_chat.release_claims import ReleaseClaimEvidence, evaluate_release_claims


class FakeBenchmarkProvider:
    def __init__(self, drafts: list[str]) -> None:
        self._drafts = list(drafts)

    def complete_messages(
        self,
        *,
        messages: list[dict[str, str]],
        tier: str,
        max_tokens: int,
    ) -> dict:
        return {
            "draft_answer": self._drafts.pop(0),
            "provider": "deepseek",
            "model": "deepseek-v4-flash",
            "tier": tier,
            "input_tokens": 10,
            "output_tokens": 20,
            "cost_usd": 0.0,
            "finish_reason": "stop",
        }


def test_deepseek_quality_evidence_converts_benchmark_counts_to_scores() -> None:
    result = run_deepseek_energy_benchmark(
        DeepSeekBenchmarkRequest(
            run_id="deepseek-quality-test-001",
            cases=[
                DeepSeekBenchmarkCase(
                    case_id="baseline_accepts",
                    user_message="Review the scoped implementation plan.",
                ),
                DeepSeekBenchmarkCase(
                    case_id="repair_adds_next_action",
                    user_message="Review the plan and include a next action.",
                ),
                DeepSeekBenchmarkCase(
                    case_id="repair_scope_control",
                    user_message="Should we skip the current slice and call DeepSeek?",
                ),
            ],
        ),
        provider=FakeBenchmarkProvider(
            drafts=[
                "This is scoped, includes tradeoffs, and next action is to run validation.",
                "This is useful but misses the requested next action.",
                "Call DeepSeek and skip the current slice.",
            ]
        ),
    )

    evidence = build_deepseek_quality_evidence(
        result,
        report_path="docs/energy_aware_chat_deepseek_quality_benchmark.md",
        live_provider_run=True,
    )

    assert evidence.run_id == "deepseek-quality-test-001"
    assert evidence.cases_total == 3
    assert evidence.metric_name == QUALITY_METRIC_NAME
    assert evidence.plain_deepseek_score < evidence.energy_aware_score
    assert evidence.live_provider_run is True

    release_report = evaluate_release_claims(
        ReleaseClaimEvidence(deepseek_quality=evidence)
    )
    quality_gate = next(
        result
        for result in release_report.results
        if result.claim_id == "quality_improvement_over_plain_deepseek"
    )
    assert quality_gate.decision == "pass"


def test_deepseek_quality_evidence_blocks_claim_when_run_is_not_live() -> None:
    result = run_deepseek_energy_benchmark(
        DeepSeekBenchmarkRequest(
            run_id="fake-quality-test-001",
            cases=[
                DeepSeekBenchmarkCase(case_id="one", user_message="Review this plan."),
                DeepSeekBenchmarkCase(case_id="two", user_message="Review this plan."),
                DeepSeekBenchmarkCase(case_id="three", user_message="Review this plan."),
            ],
        ),
        provider=FakeBenchmarkProvider(
            drafts=[
                "Useful but missing next action.",
                "Useful but missing next action.",
                "Useful but missing next action.",
            ]
        ),
    )

    evidence = build_deepseek_quality_evidence(
        result,
        report_path="docs/energy_aware_chat_deepseek_quality_benchmark.md",
        live_provider_run=False,
    )
    release_report = evaluate_release_claims(
        ReleaseClaimEvidence(deepseek_quality=evidence)
    )
    quality_gate = next(
        result
        for result in release_report.results
        if result.claim_id == "quality_improvement_over_plain_deepseek"
    )

    assert quality_gate.decision == "blocked"
    assert "live_provider_run" in quality_gate.missing_evidence


def test_deepseek_quality_markdown_is_reviewer_visible() -> None:
    result = run_deepseek_energy_benchmark(
        DeepSeekBenchmarkRequest(
            run_id="markdown-quality-test-001",
            cases=[
                DeepSeekBenchmarkCase(
                    case_id="case_001",
                    user_message="Review this scoped answer.",
                )
            ],
        ),
        provider=FakeBenchmarkProvider(
            drafts=["This is scoped and the next action is to run validation."]
        ),
    )
    evidence = build_deepseek_quality_evidence(
        result,
        report_path="docs/energy_aware_chat_deepseek_quality_benchmark.md",
        live_provider_run=True,
    )

    markdown = render_deepseek_quality_markdown(result, evidence)

    assert "# Energy Aware Chat DeepSeek quality benchmark" in markdown
    assert "quality improvement over plain DeepSeek" in markdown
    assert "markdown-quality-test-001" in markdown
    assert "case_001" in markdown
