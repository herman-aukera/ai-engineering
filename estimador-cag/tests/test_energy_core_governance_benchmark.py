"""Tests for the deterministic governance contract benchmark."""

from energy_core.governance_benchmark import (
    GovernanceBenchmarkCase,
    run_governance_benchmark,
)


def test_default_benchmark_matches_cases_and_improves_contract_accuracy() -> None:
    report = run_governance_benchmark()

    assert report.total_cases == 4
    assert report.single_correct == 1
    assert report.governed_correct == 4
    assert report.governed_delta == 3
    assert report.governance_improves_contract_accuracy is True
    assert "not evidence" in report.claim_boundary


def test_governed_results_match_every_expected_disposition() -> None:
    report = run_governance_benchmark()
    governed = [result for result in report.results if result.mode == "governed"]

    assert len(governed) == report.total_cases
    assert all(result.correct for result in governed)


def test_benchmark_does_not_invent_improvement_when_modes_tie() -> None:
    cases = (
        GovernanceBenchmarkCase(
            case_id="clean-only",
            findings=(
                {"owner": "proposer", "disposition": "accept"},
                {"owner": "critic", "disposition": "accept"},
            ),
            expected_disposition="accept",
        ),
    )

    report = run_governance_benchmark(cases)

    assert report.single_correct == 1
    assert report.governed_correct == 1
    assert report.governed_delta == 0
    assert report.governance_improves_contract_accuracy is False


def test_benchmark_rejects_empty_case_set() -> None:
    try:
        run_governance_benchmark(())
    except ValueError as exc:
        assert "At least one" in str(exc)
    else:
        raise AssertionError("empty benchmark set must fail closed")
