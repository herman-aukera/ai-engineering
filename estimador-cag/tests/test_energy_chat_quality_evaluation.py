"""Milestone 19: quality evaluation benchmark — rubric, scoring, aggregation."""

from __future__ import annotations

from app.energy_chat.quality_evaluation import (
    DEFAULT_RUBRIC,
    QualityBenchmarkCase,
    build_quality_benchmark_run,
    evaluate_quality_case,
)


def test_default_rubric_has_eight_dimensions() -> None:
    assert len(DEFAULT_RUBRIC.dimensions) == 8
    assert DEFAULT_RUBRIC.claim_status == "measurement_only_no_quality_claim"


def test_default_rubric_weights_sum_near_one() -> None:
    total = sum(d.weight for d in DEFAULT_RUBRIC.dimensions)
    assert 0.99 <= total <= 1.01


def test_evaluate_quality_case_passes_when_all_gold_met() -> None:
    case = QualityBenchmarkCase(
        case_id="q-1",
        category="architecture",
        user_message="Explain the graph backbone.",
        gold_constraints=["no secrets"],
        gold_evidence_refs=["source:architecture"],
    )
    result = evaluate_quality_case(
        case,
        disposition="accept",
        energy=80,
        latency_ms=5_000,
        cost_usd=0.01,
        evidence_refs=["source:architecture", "source:sdd"],
    )
    assert result.passed is True
    assert result.energy_pass is True
    assert result.latency_pass is True
    assert result.cost_pass is True
    assert result.evidence_match is True


def test_evaluate_quality_case_fails_when_energy_exceeded() -> None:
    case = QualityBenchmarkCase(
        case_id="q-2",
        category="deployment",
        user_message="Is Docker required?",
        max_acceptable_energy=50,
    )
    result = evaluate_quality_case(case, disposition="accept", energy=200)
    assert result.passed is False
    assert result.energy_pass is False


def test_evaluate_quality_case_fails_on_wrong_disposition() -> None:
    case = QualityBenchmarkCase(
        case_id="q-3",
        category="safety",
        user_message="Test refusal.",
        gold_disposition="accept",
    )
    result = evaluate_quality_case(case, disposition="refuse", energy=0)
    assert result.passed is False


def test_evaluate_quality_case_fails_on_missing_evidence() -> None:
    case = QualityBenchmarkCase(
        case_id="q-4",
        category="evidence",
        user_message="Test evidence.",
        gold_evidence_refs=["source:required_doc"],
    )
    result = evaluate_quality_case(
        case, disposition="accept", energy=50, evidence_refs=["source:other"]
    )
    assert result.evidence_match is False
    assert result.passed is False


def test_build_quality_benchmark_run_aggregates_results() -> None:
    results = [
        evaluate_quality_case(
            QualityBenchmarkCase(case_id="a", category="c", user_message="u1"),
            disposition="accept", energy=50,
        ),
        evaluate_quality_case(
            QualityBenchmarkCase(case_id="b", category="c", user_message="u2"),
            disposition="accept", energy=50,
        ),
        evaluate_quality_case(
            QualityBenchmarkCase(case_id="c", category="c", user_message="u3"),
            disposition="refuse", energy=500,
        ),
    ]
    run = build_quality_benchmark_run(
        run_id="test-run",
        provider="deepseek",
        model="deepseek-v4-flash",
        results=results,
    )
    assert run.cases_total == 3
    assert run.cases_passed == 2
    assert run.pass_rate == 2 / 3
    assert run.claim_status == "measurement_only_no_quality_claim"
    assert run.provider == "deepseek"


def test_quality_benchmark_case_defaults() -> None:
    case = QualityBenchmarkCase(
        case_id="defaults", category="test", user_message="test"
    )
    assert case.gold_disposition == "accept"
    assert case.max_acceptable_energy == 120
    assert case.max_acceptable_latency_ms == 30_000
    assert case.max_acceptable_cost_usd == 0.05
