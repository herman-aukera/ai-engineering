from app.energy_chat.release_claims import (
    DeepSeekQualityEvidence,
    FrontierComparisonEvidence,
    ProductionReadinessEvidence,
    PublicDeploymentEvidence,
    ReleaseClaimEvidence,
    evaluate_release_claims,
)


def test_release_claims_block_high_risk_phrases_without_evidence() -> None:
    report = evaluate_release_claims(ReleaseClaimEvidence())

    assert report.overall_ready is False
    assert report.claim_status == "release_claims_blocked_missing_evidence"

    decisions = {result.claim_id: result for result in report.results}
    assert decisions["production_ready"].decision == "blocked"
    assert decisions["public_deployment_live"].decision == "blocked"
    assert decisions["quality_improvement_over_plain_deepseek"].decision == "blocked"
    assert decisions["frontier_model_superiority"].decision == "blocked"

    assert "public_deployment_live" in decisions["production_ready"].missing_evidence
    assert "live_provider_run" in decisions[
        "quality_improvement_over_plain_deepseek"
    ].missing_evidence
    assert "at_least_two_frontier_models_tested" in decisions[
        "frontier_model_superiority"
    ].missing_evidence


def test_quality_improvement_claim_requires_energy_aware_score_to_beat_plain_deepseek() -> None:
    evidence = ReleaseClaimEvidence(
        deepseek_quality=DeepSeekQualityEvidence(
            run_id="deepseek-live-001",
            cases_total=5,
            plain_deepseek_score=0.82,
            energy_aware_score=0.82,
            metric_name="hard_constraint_pass_rate",
            report_path="evals/energy_chat/deepseek_quality_report.md",
            live_provider_run=True,
        )
    )

    report = evaluate_release_claims(evidence)
    quality_gate = next(
        result
        for result in report.results
        if result.claim_id == "quality_improvement_over_plain_deepseek"
    )

    assert quality_gate.decision == "blocked"
    assert (
        "energy_aware_score_greater_than_plain_deepseek_score"
        in quality_gate.missing_evidence
    )


def test_quality_improvement_claim_passes_with_bounded_live_benchmark_evidence() -> None:
    evidence = ReleaseClaimEvidence(
        deepseek_quality=DeepSeekQualityEvidence(
            run_id="deepseek-live-001",
            cases_total=5,
            plain_deepseek_score=0.6,
            energy_aware_score=0.8,
            metric_name="hard_constraint_pass_rate",
            report_path="evals/energy_chat/deepseek_quality_report.md",
            live_provider_run=True,
        )
    )

    report = evaluate_release_claims(evidence)
    quality_gate = next(
        result
        for result in report.results
        if result.claim_id == "quality_improvement_over_plain_deepseek"
    )

    assert quality_gate.decision == "pass"
    assert quality_gate.missing_evidence == []


def test_all_release_claims_pass_only_with_complete_operational_evidence() -> None:
    evidence = ReleaseClaimEvidence(
        production=ProductionReadinessEvidence(
            public_deployment=PublicDeploymentEvidence(
                public_url="https://example.com",
                healthcheck_passed=True,
                demo_route_passed=True,
                timestamp_utc="2026-06-15T21:00:00Z",
            ),
            ci_green=True,
            deterministic_validation_green=True,
            secret_scan_green=True,
            rollback_documented=True,
            observability_documented=True,
            privacy_boundary_documented=True,
            incident_response_documented=True,
            real_user_monitoring_documented=True,
        ),
        deepseek_quality=DeepSeekQualityEvidence(
            run_id="deepseek-live-001",
            cases_total=5,
            plain_deepseek_score=0.6,
            energy_aware_score=0.8,
            metric_name="hard_constraint_pass_rate",
            report_path="evals/energy_chat/deepseek_quality_report.md",
            live_provider_run=True,
        ),
        frontier_comparison=FrontierComparisonEvidence(
            benchmark_run_id="frontier-001",
            frontier_models_tested=["model-a", "model-b"],
            benchmark_report_path="evals/energy_chat/frontier_report.md",
            independent_rubric=True,
            same_task_set=True,
            cost_and_latency_reported=True,
            human_review_notes_present=True,
        ),
    )

    report = evaluate_release_claims(evidence)

    assert report.overall_ready is True
    assert report.claim_status == "all_release_claims_evidence_backed"
    assert {result.decision for result in report.results} == {"pass"}
