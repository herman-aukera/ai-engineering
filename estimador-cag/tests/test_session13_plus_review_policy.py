from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.review_policy import (
    CriticFinding,
    CriticReport,
    ExecutionBudgetSnapshot,
)
from app.services.review_policy import (
    boss_decision_to_domain_event,
    route_review_policy,
)


def _finding(
    *,
    code: str = "retrieval_gap",
    severity: str = "major",
    repair_scope: str = "selected_component",
) -> CriticFinding:
    return CriticFinding(
        code=code,
        severity=severity,
        state_path="component_estimates.cmp-auth",
        explanation="The selected component does not have enough supporting evidence.",
        evidence_refs=["cmp-auth", "CH-101"],
        proposed_repair=(
            "Re-run retrieval for the selected component."
            if repair_scope != "none"
            else None
        ),
        repair_scope=repair_scope,
        component_ids=["cmp-auth"] if repair_scope in {"selected_component", "human"} else [],
        node="generate_estimate",
    )


def _report(
    *,
    verdict: str,
    issues: list[CriticFinding] | None = None,
) -> CriticReport:
    return CriticReport(
        verdict=verdict,
        issues=issues or [],
        confidence_in_review=0.91,
        summary="Structured review completed against evidence and invariants.",
    )


def test_critic_finding_requires_repair_for_non_none_scope() -> None:
    with pytest.raises(ValidationError, match="must include proposed_repair"):
        CriticFinding(
            code="retrieval_gap",
            severity="major",
            state_path="budget_matches",
            explanation="Historical evidence is incomplete for this component.",
            proposed_repair=None,
            repair_scope="selected_node",
            node="search_budgets",
        )


def test_accept_report_rejects_major_issue() -> None:
    with pytest.raises(ValidationError, match="cannot contain major or critical"):
        _report(verdict="accept", issues=[_finding()])


def test_critical_arithmetic_failure_is_rejected_before_retry() -> None:
    report = _report(
        verdict="needs_iteration",
        issues=[
            _finding(
                code="arithmetic_mismatch",
                severity="critical",
                repair_scope="full_graph",
            )
        ],
    )

    decision = route_review_policy(
        report=report,
        budgets=ExecutionBudgetSnapshot(),
    )

    assert decision.action == "reject"
    assert decision.issue_codes == ["arithmetic_mismatch"]


def test_provider_timeout_uses_bounded_fallback() -> None:
    report = _report(verdict="accept")

    decision = route_review_policy(
        report=report,
        budgets=ExecutionBudgetSnapshot(
            fallback_count=0,
            fallback_limit=1,
        ),
        provider_failure="timeout",
        fallback_provider="kimi-k2.6",
    )

    assert decision.action == "fallback_provider"
    assert decision.next_provider == "kimi-k2.6"
    assert decision.remaining_fallback_budget == 1


def test_provider_failure_escalates_when_fallback_budget_is_exhausted() -> None:
    report = _report(verdict="accept")

    decision = route_review_policy(
        report=report,
        budgets=ExecutionBudgetSnapshot(
            fallback_count=1,
            fallback_limit=1,
        ),
        provider_failure="unavailable",
        fallback_provider="kimi-k2.6",
    )

    assert decision.action == "human_review"
    assert decision.remaining_fallback_budget == 0


def test_conflicting_evidence_requires_human_review() -> None:
    report = _report(
        verdict="human_required",
        issues=[
            _finding(
                code="conflicting_evidence",
                severity="major",
                repair_scope="human",
            )
        ],
    )

    decision = route_review_policy(
        report=report,
        budgets=ExecutionBudgetSnapshot(),
    )

    assert decision.action == "human_review"
    assert decision.selected_component_ids == ["cmp-auth"]


def test_repairable_issue_retries_only_selected_scope_when_budget_exists() -> None:
    report = _report(verdict="needs_iteration", issues=[_finding()])

    decision = route_review_policy(
        report=report,
        budgets=ExecutionBudgetSnapshot(
            retry_count=0,
            retry_limit=2,
        ),
    )

    assert decision.action == "retry_selected"
    assert decision.selected_state_paths == ["component_estimates.cmp-auth"]
    assert decision.selected_component_ids == ["cmp-auth"]
    assert decision.remaining_retry_budget == 2


def test_repairable_issue_escalates_when_retry_budget_is_exhausted() -> None:
    report = _report(verdict="needs_iteration", issues=[_finding()])

    decision = route_review_policy(
        report=report,
        budgets=ExecutionBudgetSnapshot(
            retry_count=2,
            retry_limit=2,
        ),
    )

    assert decision.action == "human_review"
    assert decision.remaining_retry_budget == 0


def test_clean_report_is_accepted() -> None:
    decision = route_review_policy(
        report=_report(verdict="accept"),
        budgets=ExecutionBudgetSnapshot(),
    )

    assert decision.action == "accept"
    assert decision.issue_codes == []


def test_boss_decision_emits_checkpoint_safe_domain_event() -> None:
    decision = route_review_policy(
        report=_report(verdict="needs_iteration", issues=[_finding()]),
        budgets=ExecutionBudgetSnapshot(),
    )

    event = boss_decision_to_domain_event(decision)

    assert event == {
        "event_type": "boss_retry_selected",
        "node": "boss_policy",
        "summary": decision.reason,
        "evidence_refs": ["retrieval_gap"],
        "state_delta_keys": ["boss_decision", "status"],
    }
