from pathlib import Path

from app.energy_chat.fixed_benchmark import (
    DEFAULT_FIXED_BENCHMARK_PATH,
    FixedBenchmarkCase,
    load_fixed_benchmark_cases,
    render_fixed_benchmark_markdown,
    run_fixed_benchmark,
)


def test_fixed_benchmark_dataset_exists_and_loads() -> None:
    cases = load_fixed_benchmark_cases()

    assert DEFAULT_FIXED_BENCHMARK_PATH.exists()
    assert len(cases) >= 5
    assert all(isinstance(case, FixedBenchmarkCase) for case in cases)
    assert {case.case_id for case in cases} >= {
        "project_deployment_evidence",
        "benchmark_honesty_boundary",
        "hidden_reasoning_refusal",
    }


def test_fixed_benchmark_cases_have_required_guardrails() -> None:
    cases = load_fixed_benchmark_cases()

    for case in cases:
        assert case.user_message.strip()
        assert case.baseline_draft_answer.strip()
        assert case.required_sections
        assert case.evidence_refs
        assert case.must_include
        assert case.must_not_include


def test_fixed_benchmark_proves_bounded_deterministic_energy_reduction() -> None:
    result = run_fixed_benchmark(run_id="test-fixed-benchmark")

    assert result.run_id == "test-fixed-benchmark"
    assert result.cases_total >= 5
    assert result.metadata["provider_calls"] == 0
    assert result.metadata["live_provider_required"] is False
    assert result.metadata["live_provider_quality_proven"] is False
    assert result.dataset_path == "evals/energy_chat/fixed_benchmark_cases.jsonl"
    assert result.accepted_baseline <= result.cases_total
    assert result.accepted_after_repair <= result.cases_total
    assert result.mean_final_energy < result.mean_baseline_energy
    assert result.average_energy_delta_after_repair < 0
    assert result.energy_improved_cases > 0
    assert result.accepted_hard_reject_exposures == 0
    assert result.quality_claim_allowed is True
    assert result.quality_claim == "deterministic_fixed_corpus_energy_reduction"
    assert result.metadata["claim_status"] == result.quality_claim
    assert result.metadata["claim_scope"] == "committed deterministic corpus only"
    assert all(item.case.case_id for item in result.results)


def test_fixed_benchmark_report_preserves_live_provider_boundary() -> None:
    result = run_fixed_benchmark(run_id="test-fixed-benchmark")
    report = render_fixed_benchmark_markdown(result)

    assert "Energy Aware Chat Fixed Benchmark Report" in report
    assert "deterministic_fixed_corpus_energy_reduction" in report
    assert "committed deterministic corpus only" in report
    assert "does not prove live provider quality improvement" in report
    assert "separate credentialed live-provider benchmark" in report


def test_fixed_benchmark_loader_rejects_invalid_jsonl(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.jsonl"
    invalid.write_text("{not json}\n", encoding="utf-8")

    try:
        load_fixed_benchmark_cases(invalid)
    except ValueError as exc:
        assert "Invalid JSONL" in str(exc)
    else:  # pragma: no cover - explicit failure branch for readability
        raise AssertionError("invalid JSONL should raise ValueError")
