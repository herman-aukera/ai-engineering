from energy_core.beta_evaluation import (
    default_beta_cases,
    run_beta_evaluation,
)


def test_versioned_golden_set_covers_required_failure_classes() -> None:
    cases = default_beta_cases()
    assert {case.case_id for case in cases} == {
        "valid-work",
        "scope-drift",
        "test-weakening",
        "secret",
        "unsafe-command",
        "missing-evidence",
        "oversized-diff",
        "stale-spec",
        "repairable-semantic-defect",
        "human-review",
        "provider-failure",
        "compaction-loss",
    }


def test_four_modes_execute_identical_cases_and_governor_preserves_hard_gates() -> None:
    report = run_beta_evaluation()

    assert report.version == "0012.0"
    assert report.modes == (
        "unchecked_agent",
        "hard_gates_only",
        "single_semantic_judge",
        "jury_action_governor",
    )
    assert len(report.results) == len(report.cases) * len(report.modes)
    assert report.correct_by_mode["jury_action_governor"] == len(report.cases)
    secret = next(
        row
        for row in report.results
        if row.case_id == "secret" and row.mode == "jury_action_governor"
    )
    assert secret.actual == "reject"


def test_expected_label_cannot_control_actual_decision() -> None:
    valid = default_beta_cases()[0]
    poisoned = valid.model_copy(update={"expected": "reject"})

    report = run_beta_evaluation((poisoned,))
    final = next(row for row in report.results if row.mode == "jury_action_governor")

    assert final.expected == "reject"
    assert final.actual == "accept"
    assert final.correct is False
