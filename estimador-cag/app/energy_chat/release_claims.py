"""Release claim gates for Energy Aware Chat.

This module makes high-risk release claims evidence-gated rather than rhetorical.
It is intentionally deterministic and does not call external providers.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

ClaimDecision = Literal["pass", "blocked"]
ClaimId = Literal[
    "production_ready",
    "public_deployment_live",
    "quality_improvement_over_plain_deepseek",
    "frontier_model_superiority",
]


class DeepSeekQualityEvidence(BaseModel):
    """Evidence for a bounded DeepSeek baseline comparison claim."""

    run_id: str | None = None
    cases_total: int = 0
    plain_deepseek_score: float | None = None
    energy_aware_score: float | None = None
    metric_name: str | None = None
    report_path: str | None = None
    live_provider_run: bool = False


class PublicDeploymentEvidence(BaseModel):
    """Evidence that the app is publicly deployed and reachable."""

    public_url: HttpUrl | None = None
    healthcheck_passed: bool = False
    demo_route_passed: bool = False
    timestamp_utc: str | None = None


class ProductionReadinessEvidence(BaseModel):
    """Evidence required before using a production-ready claim."""

    public_deployment: PublicDeploymentEvidence = Field(
        default_factory=PublicDeploymentEvidence
    )
    ci_green: bool = False
    deterministic_validation_green: bool = False
    secret_scan_green: bool = False
    rollback_documented: bool = False
    observability_documented: bool = False
    privacy_boundary_documented: bool = False
    incident_response_documented: bool = False
    real_user_monitoring_documented: bool = False


class FrontierComparisonEvidence(BaseModel):
    """Evidence required for any frontier-model superiority claim."""

    benchmark_run_id: str | None = None
    frontier_models_tested: list[str] = Field(default_factory=list)
    benchmark_report_path: str | None = None
    independent_rubric: bool = False
    same_task_set: bool = False
    cost_and_latency_reported: bool = False
    human_review_notes_present: bool = False


class ReleaseClaimEvidence(BaseModel):
    """Complete evidence packet used by release claim gates."""

    production: ProductionReadinessEvidence = Field(
        default_factory=ProductionReadinessEvidence
    )
    deepseek_quality: DeepSeekQualityEvidence = Field(
        default_factory=DeepSeekQualityEvidence
    )
    frontier_comparison: FrontierComparisonEvidence = Field(
        default_factory=FrontierComparisonEvidence
    )


class ClaimGateResult(BaseModel):
    """One deterministic release claim decision."""

    claim_id: ClaimId
    allowed_phrase: str
    decision: ClaimDecision
    missing_evidence: list[str] = Field(default_factory=list)
    reasoning_summary: str
    next_action: str


class ReleaseClaimGateReport(BaseModel):
    """Full release-claim report."""

    overall_ready: bool
    claim_status: str
    results: list[ClaimGateResult]


def evaluate_release_claims(evidence: ReleaseClaimEvidence) -> ReleaseClaimGateReport:
    """Evaluate the four high-risk claims against explicit evidence."""

    results = [
        _public_deployment_gate(evidence.production.public_deployment),
        _quality_improvement_gate(evidence.deepseek_quality),
        _frontier_superiority_gate(evidence.frontier_comparison),
        _production_ready_gate(evidence.production),
    ]
    overall_ready = all(result.decision == "pass" for result in results)
    return ReleaseClaimGateReport(
        overall_ready=overall_ready,
        claim_status=(
            "all_release_claims_evidence_backed"
            if overall_ready
            else "release_claims_blocked_missing_evidence"
        ),
        results=results,
    )


def _public_deployment_gate(
    evidence: PublicDeploymentEvidence,
) -> ClaimGateResult:
    missing = []
    if evidence.public_url is None:
        missing.append("public_url")
    if not evidence.healthcheck_passed:
        missing.append("healthcheck_passed")
    if not evidence.demo_route_passed:
        missing.append("demo_route_passed")
    if evidence.timestamp_utc is None:
        missing.append("timestamp_utc")

    return _build_result(
        claim_id="public_deployment_live",
        allowed_phrase="public deployment is live",
        missing=missing,
        pass_summary="A public URL, healthcheck, demo route, and timestamp are present.",
        fail_summary="Public deployment cannot be claimed until a live public URL is smoke-tested.",
        next_action="Deploy the Docker/FastAPI app to a public host and record URL plus smoke output.",
    )


def _quality_improvement_gate(evidence: DeepSeekQualityEvidence) -> ClaimGateResult:
    missing = []
    if not evidence.live_provider_run:
        missing.append("live_provider_run")
    if not evidence.run_id:
        missing.append("run_id")
    if evidence.cases_total < 3:
        missing.append("cases_total_at_least_3")
    if evidence.plain_deepseek_score is None:
        missing.append("plain_deepseek_score")
    if evidence.energy_aware_score is None:
        missing.append("energy_aware_score")
    if not evidence.metric_name:
        missing.append("metric_name")
    if not evidence.report_path:
        missing.append("report_path")
    if (
        evidence.plain_deepseek_score is not None
        and evidence.energy_aware_score is not None
        and evidence.energy_aware_score <= evidence.plain_deepseek_score
    ):
        missing.append("energy_aware_score_greater_than_plain_deepseek_score")

    return _build_result(
        claim_id="quality_improvement_over_plain_deepseek",
        allowed_phrase="quality improvement over plain DeepSeek",
        missing=missing,
        pass_summary="A live DeepSeek comparison shows energy-aware output scored higher under a named metric.",
        fail_summary="Quality improvement over plain DeepSeek is blocked until a live comparison report exists.",
        next_action="Run a fixed live DeepSeek benchmark and commit the result plus report.",
    )


def _frontier_superiority_gate(
    evidence: FrontierComparisonEvidence,
) -> ClaimGateResult:
    missing = []
    if not evidence.benchmark_run_id:
        missing.append("benchmark_run_id")
    if len(evidence.frontier_models_tested) < 2:
        missing.append("at_least_two_frontier_models_tested")
    if not evidence.benchmark_report_path:
        missing.append("benchmark_report_path")
    if not evidence.independent_rubric:
        missing.append("independent_rubric")
    if not evidence.same_task_set:
        missing.append("same_task_set")
    if not evidence.cost_and_latency_reported:
        missing.append("cost_and_latency_reported")
    if not evidence.human_review_notes_present:
        missing.append("human_review_notes_present")

    return _build_result(
        claim_id="frontier_model_superiority",
        allowed_phrase="frontier-model superiority",
        missing=missing,
        pass_summary="A fair bounded frontier comparison exists with rubric, same tasks, cost, latency, and review notes.",
        fail_summary="Frontier-model superiority is blocked because it requires a fair current multi-model benchmark.",
        next_action="Do not use this claim for the final project unless a fair frontier benchmark is actually run.",
    )


def _production_ready_gate(evidence: ProductionReadinessEvidence) -> ClaimGateResult:
    missing = []
    public_deployment = _public_deployment_gate(evidence.public_deployment)
    if public_deployment.decision != "pass":
        missing.append("public_deployment_live")
    if not evidence.ci_green:
        missing.append("ci_green")
    if not evidence.deterministic_validation_green:
        missing.append("deterministic_validation_green")
    if not evidence.secret_scan_green:
        missing.append("secret_scan_green")
    if not evidence.rollback_documented:
        missing.append("rollback_documented")
    if not evidence.observability_documented:
        missing.append("observability_documented")
    if not evidence.privacy_boundary_documented:
        missing.append("privacy_boundary_documented")
    if not evidence.incident_response_documented:
        missing.append("incident_response_documented")
    if not evidence.real_user_monitoring_documented:
        missing.append("real_user_monitoring_documented")

    return _build_result(
        claim_id="production_ready",
        allowed_phrase="production-ready",
        missing=missing,
        pass_summary="Production readiness evidence covers deployment, CI, secrets, rollback, observability, privacy, incident response, and monitoring.",
        fail_summary="Production-ready is blocked until operational evidence exists, not only code and tests.",
        next_action="Treat the project as production-oriented until deployment and operations evidence exists.",
    )


def _build_result(
    *,
    claim_id: ClaimId,
    allowed_phrase: str,
    missing: list[str],
    pass_summary: str,
    fail_summary: str,
    next_action: str,
) -> ClaimGateResult:
    decision: ClaimDecision = "pass" if not missing else "blocked"
    return ClaimGateResult(
        claim_id=claim_id,
        allowed_phrase=allowed_phrase,
        decision=decision,
        missing_evidence=missing,
        reasoning_summary=pass_summary if decision == "pass" else fail_summary,
        next_action="claim_allowed" if decision == "pass" else next_action,
    )
