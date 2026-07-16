"""Deterministic Critic and Boss nodes for the Session 13 Plus reviewed graph."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping

from app.generation.graph.review_state import ReviewedEstimationGraphState
from app.schemas.review_policy import (
    CriticFinding,
    CriticIssueCode,
    CriticReport,
    ExecutionBudgetSnapshot,
)
from app.services.review_policy import (
    boss_decision_to_domain_event,
    route_review_policy,
)

ReviewPolicyNode = Callable[
    [ReviewedEstimationGraphState],
    Awaitable[ReviewedEstimationGraphState],
]


def _recovery_attempted(state: ReviewedEstimationGraphState) -> bool:
    return state.get("recovery_status") in {
        "skipped",
        "completed",
        "partial",
        "failed",
    }


def _current_grounding_statuses(
    state: ReviewedEstimationGraphState,
) -> set[str]:
    return {
        str(estimate.get("grounding_status"))
        for estimate in state.get("component_estimates", [])
        if isinstance(estimate, Mapping) and estimate.get("grounding_status")
    }


def _component_findings(
    state: ReviewedEstimationGraphState,
) -> list[CriticFinding]:
    findings: list[CriticFinding] = []
    raw_estimates = state.get("component_estimates", [])
    if not isinstance(raw_estimates, list):
        return findings

    recovery_attempted = _recovery_attempted(state)
    for raw_estimate in raw_estimates:
        if not isinstance(raw_estimate, Mapping):
            continue
        component_id = str(raw_estimate.get("component_id") or "unknown")
        grounding_status = raw_estimate.get("grounding_status")
        reference_budget_ids = [
            str(value)
            for value in raw_estimate.get("reference_budget_ids", [])
        ]

        if grounding_status == "no_data":
            findings.append(
                CriticFinding(
                    code=CriticIssueCode.NO_DATA,
                    severity="major",
                    state_path=f"component_estimates.{component_id}",
                    explanation="The component has no recorded-hours evidence.",
                    evidence_refs=[component_id, *reference_budget_ids],
                    proposed_repair=(
                        "Provide or approve a human baseline for this unresolved component."
                        if recovery_attempted
                        else "Run selective retrieval recovery for this component."
                    ),
                    repair_scope="human" if recovery_attempted else "selected_component",
                    component_ids=[component_id],
                    node="generate_estimate",
                )
            )
        elif grounding_status == "conflict":
            findings.append(
                CriticFinding(
                    code=CriticIssueCode.CONFLICTING_EVIDENCE,
                    severity="major",
                    state_path=f"component_estimates.{component_id}",
                    explanation="Historical hour references conflict beyond policy tolerance.",
                    evidence_refs=[component_id, *reference_budget_ids],
                    proposed_repair=(
                        "Review the conflicting sources and approve or replace the baseline."
                    ),
                    repair_scope="human",
                    component_ids=[component_id],
                    node="generate_estimate",
                )
            )
        elif grounding_status == "low_confidence":
            findings.append(
                CriticFinding(
                    code=CriticIssueCode.UNRELIABLE_ESTIMATE,
                    severity="major" if recovery_attempted else "minor",
                    state_path=f"component_estimates.{component_id}",
                    explanation="The component estimate has insufficient or dispersed evidence.",
                    evidence_refs=[component_id, *reference_budget_ids],
                    proposed_repair=(
                        "Approve or replace the low-confidence baseline."
                        if recovery_attempted
                        else "Re-run retrieval for the selected component."
                    ),
                    repair_scope="human" if recovery_attempted else "selected_component",
                    component_ids=[component_id],
                    node="generate_estimate",
                )
            )
    return findings


def _error_is_superseded(
    *,
    raw_code: str,
    grounding_statuses: set[str],
    resolved_issue_codes: set[str],
) -> bool:
    if raw_code in resolved_issue_codes:
        return True
    if "missing_component_evidence" in raw_code:
        return "no_data" not in grounding_statuses
    if "low_confidence_component_estimate" in raw_code:
        return "low_confidence" not in grounding_statuses
    if "conflicting_component_evidence" in raw_code:
        return "conflict" not in grounding_statuses
    return False


def _error_findings(
    state: ReviewedEstimationGraphState,
    *,
    existing_codes: set[CriticIssueCode],
) -> list[CriticFinding]:
    findings: list[CriticFinding] = []
    raw_errors = state.get("errors", [])
    if not isinstance(raw_errors, list):
        return findings

    grounding_statuses = _current_grounding_statuses(state)
    resolved_issue_codes = {
        str(code) for code in state.get("resolved_issue_codes", [])
    }
    for raw_error in raw_errors:
        if not isinstance(raw_error, Mapping):
            continue
        raw_code = str(raw_error.get("code") or "unknown_error")
        if _error_is_superseded(
            raw_code=raw_code,
            grounding_statuses=grounding_statuses,
            resolved_issue_codes=resolved_issue_codes,
        ):
            continue

        node = str(raw_error.get("node") or "unknown")
        message = str(raw_error.get("message") or "Graph validation failed.")
        severity = "critical" if "mismatch" in raw_code else "major"

        if raw_code == "unmapped_requirements":
            issue_code = CriticIssueCode.MISSING_REQUIREMENT
            repair_scope = "selected_node"
            proposed_repair = "Reclassify components so every requirement is mapped."
        elif "conflicting" in raw_code:
            issue_code = CriticIssueCode.CONFLICTING_EVIDENCE
            repair_scope = "human"
            proposed_repair = "Review the conflicting evidence and choose an accepted baseline."
        elif "missing_component_evidence" in raw_code:
            issue_code = CriticIssueCode.NO_DATA
            repair_scope = "human" if _recovery_attempted(state) else "selected_component"
            proposed_repair = (
                "Provide or approve a human baseline for the component without evidence."
                if repair_scope == "human"
                else "Re-run retrieval for the component without evidence."
            )
        elif "mismatch" in raw_code:
            issue_code = CriticIssueCode.ARITHMETIC_MISMATCH
            repair_scope = "full_graph"
            proposed_repair = "Recalculate deterministic totals from component estimates."
        elif "trace" in raw_code:
            issue_code = CriticIssueCode.INCOMPLETE_TRACE
            repair_scope = "selected_node"
            proposed_repair = "Re-run the node and restore the required domain event."
        elif raw_code == "selective_recovery_failed":
            issue_code = CriticIssueCode.PROVIDER_RUNTIME_ANOMALY
            repair_scope = "human"
            proposed_repair = "Inspect the recovery runtime and choose a human fallback."
        else:
            issue_code = CriticIssueCode.UNRELIABLE_ESTIMATE
            repair_scope = "selected_node"
            proposed_repair = f"Re-run and validate the failing node: {node}."

        if issue_code in existing_codes and issue_code in {
            CriticIssueCode.NO_DATA,
            CriticIssueCode.CONFLICTING_EVIDENCE,
            CriticIssueCode.UNRELIABLE_ESTIMATE,
        }:
            continue

        findings.append(
            CriticFinding(
                code=issue_code,
                severity=severity,
                state_path=f"errors.{raw_code}",
                explanation=message,
                evidence_refs=[raw_code],
                proposed_repair=proposed_repair,
                repair_scope=repair_scope,
                node=node,
            )
        )
    return findings


def build_deterministic_critic_node() -> ReviewPolicyNode:
    """Build a Critic that emits typed findings without changing estimates."""

    async def deterministic_critic(
        state: ReviewedEstimationGraphState,
    ) -> ReviewedEstimationGraphState:
        findings = _component_findings(state)
        findings.extend(
            _error_findings(
                state,
                existing_codes={finding.code for finding in findings},
            )
        )

        if any(
            finding.severity == "critical"
            and finding.code
            in {
                CriticIssueCode.ARITHMETIC_MISMATCH,
                CriticIssueCode.POLICY_VIOLATION,
            }
            for finding in findings
        ):
            verdict = "reject"
        elif any(
            finding.repair_scope == "human"
            and finding.severity in {"major", "critical"}
            for finding in findings
        ):
            verdict = "human_required"
        elif any(finding.repair_scope != "none" for finding in findings):
            verdict = "needs_iteration"
        else:
            verdict = "accept"

        report = CriticReport(
            verdict=verdict,
            issues=findings,
            confidence_in_review=1.0,
            summary=(
                "Deterministic Critic found no policy issues."
                if not findings
                else f"Deterministic Critic produced {len(findings)} structured findings."
            ),
        )
        return {
            "critic_report": report.model_dump(mode="json"),
            "trace_events": [
                {
                    "event_type": "critic_review_completed",
                    "node": "deterministic_critic",
                    "summary": report.summary,
                    "evidence_refs": [str(finding.code) for finding in findings],
                    "state_delta_keys": ["critic_report", "trace_events"],
                }
            ],
        }

    return deterministic_critic


def build_deterministic_boss_node() -> ReviewPolicyNode:
    """Build the bounded Python policy router over the Critic contract."""

    async def deterministic_boss(
        state: ReviewedEstimationGraphState,
    ) -> ReviewedEstimationGraphState:
        report = CriticReport.model_validate(state.get("critic_report", {}))
        budgets = ExecutionBudgetSnapshot.model_validate(
            state.get("execution_budgets", {})
        )
        execution_metadata = state.get("execution_metadata", {})
        provider_failure = "none"
        fallback_provider = None
        if isinstance(execution_metadata, Mapping):
            raw_failure = execution_metadata.get("provider_failure")
            if raw_failure in {
                "none",
                "timeout",
                "rate_limit",
                "malformed_output",
                "unavailable",
            }:
                provider_failure = raw_failure
            raw_fallback = execution_metadata.get("fallback_provider")
            if isinstance(raw_fallback, str) and raw_fallback.strip():
                fallback_provider = raw_fallback.strip()

        decision = route_review_policy(
            report=report,
            budgets=budgets,
            provider_failure=provider_failure,
            fallback_provider=fallback_provider,
        )
        update: ReviewedEstimationGraphState = {
            "boss_decision": decision.model_dump(mode="json"),
            "trace_events": [boss_decision_to_domain_event(decision)],
        }
        if decision.action == "accept":
            update["review_required"] = False
        elif decision.action in {"human_review", "reject"}:
            update["review_required"] = True
            update["status"] = "needs_review"
        else:
            update["review_required"] = True
            update["status"] = "pending"
        return update

    return deterministic_boss
