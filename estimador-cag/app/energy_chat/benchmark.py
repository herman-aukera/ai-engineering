"""Benchmark harness for DeepSeek baseline versus Energy Aware evaluation."""

from __future__ import annotations

from uuid import uuid4

from app.energy_chat.baseline import (
    BaselineDraftProvider,
    generate_deepseek_baseline_draft,
)
from app.energy_chat.contracts import (
    DeepSeekBaselineRequest,
    DeepSeekBenchmarkRequest,
    DeepSeekBenchmarkRunResult,
    DeepSeekBenchmarkCaseResult,
    EnergyChatRequest,
)
from app.energy_chat.evaluator import evaluate_with_one_pass_repair, run_evaluation


def run_deepseek_energy_benchmark(
    request: DeepSeekBenchmarkRequest,
    *,
    provider: BaselineDraftProvider | None = None,
) -> DeepSeekBenchmarkRunResult:
    """
    Run a fixed benchmark batch without making quality improvement claims.

    This Slice 6 harness captures the plain draft, deterministic evaluation, and
    one-pass repair result for each case. Normal tests inject fake providers, so
    CI never requires live DeepSeek credentials.
    """

    results: list[DeepSeekBenchmarkCaseResult] = []
    for case in request.cases:
        baseline_request = DeepSeekBaselineRequest(
            user_message=case.user_message,
            mode=case.mode,
            tier=request.tier,
            max_tokens=request.max_tokens,
            required_constraints=case.required_constraints,
            required_sections=case.required_sections,
            metadata={"benchmark_case_id": case.case_id, **case.metadata},
        )
        baseline_result = generate_deepseek_baseline_draft(
            baseline_request,
            provider=provider,
        )
        evaluation_request = EnergyChatRequest(
            user_message=case.user_message,
            draft_answer=baseline_result.draft_answer,
            mode=case.mode,
            required_constraints=case.required_constraints,
            required_sections=case.required_sections,
            evidence_refs=baseline_result.evidence_refs,
            metadata={
                "benchmark_case_id": case.case_id,
                "baseline_provider": baseline_result.provider,
                "baseline_model": baseline_result.model,
            },
        )
        baseline_evaluation = run_evaluation(evaluation_request)
        repair_evaluation = evaluate_with_one_pass_repair(evaluation_request)
        final_result = repair_evaluation.final_result
        results.append(
            DeepSeekBenchmarkCaseResult(
                case=case,
                baseline=baseline_result,
                baseline_evaluation=baseline_evaluation,
                repair_evaluation=repair_evaluation,
                final_decision=final_result.decision.decision,
                final_energy=final_result.score.total_energy,
                energy_delta_after_repair=(
                    final_result.score.total_energy
                    - baseline_evaluation.score.total_energy
                ),
                accepted_after_repair=final_result.decision.decision == "accept",
            )
        )

    accepted_baseline = sum(
        item.baseline_evaluation.decision.decision == "accept" for item in results
    )
    accepted_after_repair = sum(item.accepted_after_repair for item in results)
    repairs_attempted = sum(item.repair_evaluation.repair_attempted for item in results)
    hard_rejects = sum(
        bool(item.baseline_evaluation.score.hard_reject_violations)
        for item in results
    )

    provider_name = results[0].baseline.provider if results else "deepseek"
    model_name = results[0].baseline.model if results else "unknown"
    return DeepSeekBenchmarkRunResult(
        run_id=request.run_id or f"energy-chat-benchmark-{uuid4().hex[:12]}",
        provider=provider_name,
        model=model_name,
        tier=request.tier,
        cases_total=len(results),
        accepted_baseline=accepted_baseline,
        accepted_after_repair=accepted_after_repair,
        repairs_attempted=repairs_attempted,
        hard_rejects=hard_rejects,
        results=results,
        metadata={
            "benchmark_family": "deepseek_baseline_vs_energy_aware",
            "claim_status": "measurement_only_no_quality_claim",
        },
    )
