from __future__ import annotations

from pathlib import Path

from app.energy_chat.contracts import (
    DeepSeekBaselineRequest,
    DeepSeekBaselineResult,
    DeepSeekBenchmarkCase,
    DeepSeekBenchmarkCaseResult,
    DeepSeekBenchmarkRunResult,
    EnergyChatRequest,
)
from app.energy_chat.evaluator import evaluate_with_one_pass_repair, run_evaluation
from app.energy_chat.reports import (
    build_deepseek_benchmark_report_markdown,
    write_deepseek_benchmark_report,
)


def _benchmark_result() -> DeepSeekBenchmarkRunResult:
    case = DeepSeekBenchmarkCase(
        case_id="scoped_case",
        user_message="Should I keep the current implementation scoped?",
    )
    baseline = DeepSeekBaselineResult(
        request=DeepSeekBaselineRequest(user_message=case.user_message),
        draft_answer=(
            "The answer stays scoped to the current deterministic slice, "
            "names the tradeoff, and the next action is to run validation."
        ),
        provider="fake-provider",
        model="fake-model",
        tier="flash",
        input_tokens=8,
        output_tokens=14,
        cost_usd=0.0,
        finish_reason="stop",
    )
    request = EnergyChatRequest(
        user_message=case.user_message,
        draft_answer=baseline.draft_answer,
    )
    baseline_evaluation = run_evaluation(request)
    repair_evaluation = evaluate_with_one_pass_repair(request)

    return DeepSeekBenchmarkRunResult(
        run_id="report-test-001",
        provider=baseline.provider,
        model=baseline.model,
        tier="flash",
        cases_total=1,
        accepted_baseline=1,
        accepted_after_repair=1,
        repairs_attempted=0,
        hard_rejects=0,
        results=[
            DeepSeekBenchmarkCaseResult(
                case=case,
                baseline=baseline,
                baseline_evaluation=baseline_evaluation,
                repair_evaluation=repair_evaluation,
                final_decision="accept",
                final_energy=0,
                energy_delta_after_repair=0,
                accepted_after_repair=True,
            )
        ],
        metadata={"claim_status": "measurement_only_no_quality_claim"},
    )


def test_build_deepseek_benchmark_report_is_measurement_only() -> None:
    report = build_deepseek_benchmark_report_markdown(_benchmark_result())

    assert "# Energy Aware Chat Benchmark Report" in report
    assert "Run ID: `report-test-001`" in report
    assert "Claim status: `measurement_only_no_quality_claim`" in report
    assert "This report is a measurement artifact only" in report
    assert "| scoped_case |" in report
    assert "Run the same fixed cases" in report


def test_write_deepseek_benchmark_report_creates_parent_directory(tmp_path: Path) -> None:
    output_path = tmp_path / "reports" / "benchmark.md"

    written_path = write_deepseek_benchmark_report(_benchmark_result(), output_path)

    assert written_path == output_path
    assert output_path.exists()
    assert "report-test-001" in output_path.read_text(encoding="utf-8")
