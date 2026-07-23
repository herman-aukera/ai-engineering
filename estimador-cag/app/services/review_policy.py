"""Deterministic Boss policy for routing structured Critic reports."""

from __future__ import annotations

from app.schemas.review_policy import (
    BossDecision,
    CriticIssueCode,
    CriticReport,
    ExecutionBudgetSnapshot,
    ProviderFailureKind,
)

_HARD_REJECT_CODES = {
    CriticIssueCode.ARITHMETIC_MISMATCH,
    CriticIssueCode.POLICY_VIOLATION,
}
_HUMAN_REVIEW_CODES = {
    CriticIssueCode.CONFLICTING_EVIDENCE,
    CriticIssueCode.NO_DATA,
    CriticIssueCode.UNSUPPORTED_SCOPE,
}


def _remaining(limit: int, count: int) -> int:
    return max(0, limit - count)


def _decision(
    *,
    action: str,
    reason: str,
    report: CriticReport,
    budgets: ExecutionBudgetSnapshot,
    next_provider: str | None = None,
) -> BossDecision:
    issues = report.issues
    return BossDecision(
        action=action,
        reason=reason,
        issue_codes=list(dict.fromkeys(issue.code for issue in issues)),
        selected_state_paths=list(dict.fromkeys(issue.state_path for issue in issues)),
        selected_component_ids=list(
            dict.fromkeys(
                component_id
                for issue in issues
                for component_id in issue.component_ids
            )
        ),
        next_provider=next_provider,
        remaining_retry_budget=_remaining(budgets.retry_limit, budgets.retry_count),
        remaining_fallback_budget=_remaining(
            budgets.fallback_limit,
            budgets.fallback_count,
        ),
        remaining_tool_call_budget=_remaining(
            budgets.tool_call_limit,
            budgets.tool_call_count,
        ),
    )


def route_review_policy(
    *,
    report: CriticReport,
    budgets: ExecutionBudgetSnapshot,
    provider_failure: ProviderFailureKind = "none",
    fallback_provider: str | None = None,
) -> BossDecision:
    """Choose one bounded action without allowing the Critic to mutate state."""

    critical_hard_failures = [
        issue
        for issue in report.issues
        if issue.severity == "critical" and issue.code in _HARD_REJECT_CODES
    ]
    if critical_hard_failures:
        return _decision(
            action="reject",
            reason="A critical arithmetic or policy invariant failed.",
            report=report,
            budgets=budgets,
        )

    if report.verdict == "reject":
        return _decision(
            action="reject",
            reason="The structured Critic rejected the estimate.",
            report=report,
            budgets=budgets,
        )

    if provider_failure != "none":
        fallback_allowed = (
            fallback_provider is not None
            and budgets.fallback_available
            and budgets.tool_budget_available
            and budgets.latency_available
            and budgets.cost_available
        )
        if fallback_allowed:
            return _decision(
                action="fallback_provider",
                reason=(
                    f"Provider failure '{provider_failure}' occurred and the bounded "
                    "fallback budget remains available."
                ),
                report=report,
                budgets=budgets,
                next_provider=fallback_provider,
            )
        return _decision(
            action="human_review",
            reason=(
                f"Provider failure '{provider_failure}' cannot be recovered within "
                "the configured fallback, cost, latency, or tool-call budgets."
            ),
            report=report,
            budgets=budgets,
        )

    human_review_issues = [
        issue
        for issue in report.issues
        if issue.code in _HUMAN_REVIEW_CODES and issue.severity in {"major", "critical"}
    ]
    if report.verdict == "human_required" or human_review_issues:
        return _decision(
            action="human_review",
            reason="Evidence or scope risk requires an explicit human decision.",
            report=report,
            budgets=budgets,
        )

    if report.verdict == "needs_iteration":
        retry_allowed = (
            budgets.retry_available
            and budgets.tool_budget_available
            and budgets.latency_available
            and budgets.cost_available
        )
        if retry_allowed:
            return _decision(
                action="retry_selected",
                reason="Repairable findings remain and the bounded retry budget is available.",
                report=report,
                budgets=budgets,
            )
        return _decision(
            action="human_review",
            reason=(
                "Repairable findings remain, but retry, cost, latency, or tool-call "
                "budget is exhausted."
            ),
            report=report,
            budgets=budgets,
        )

    return _decision(
        action="accept",
        reason="The structured Critic accepted the estimate and no hard policy gate failed.",
        report=report,
        budgets=budgets,
    )


def boss_decision_to_domain_event(decision: BossDecision) -> dict[str, object]:
    """Convert one policy decision into checkpoint-safe domain trace data."""

    evidence_refs = [str(code) for code in decision.issue_codes]
    state_delta_keys = ["boss_decision"]
    if decision.action in {"retry_selected", "fallback_provider", "human_review"}:
        state_delta_keys.append("status")

    return {
        "event_type": f"boss_{decision.action}",
        "node": "boss_policy",
        "summary": decision.reason,
        "evidence_refs": evidence_refs,
        "state_delta_keys": state_delta_keys,
    }
