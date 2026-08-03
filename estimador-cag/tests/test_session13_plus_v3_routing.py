from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.v3_routing import ComplexityAssessment, ComplexitySignals
from app.services.v3_complexity_router import assess_complexity, build_model_routing_plan


def test_simple_project_uses_low_cost_stage_specific_routes() -> None:
    assessment = assess_complexity(
        ComplexitySignals(requirement_count=3, transcript_chars=2_000),
        detected_languages=["en"],
    )

    plan = build_model_routing_plan(assessment, profile="balanced")

    assert assessment.level == "C1"
    assert assessment.human_review_required is False
    assert plan.routes_by_stage["structure"].model == "deepseek-v4-flash"
    assert plan.routes_by_stage["structure"].mode == "instant"
    assert plan.routes_by_stage["recovery"].provider == "python"
    assert plan.routes_by_stage["recovery"].mode == "deterministic"


def test_critical_project_forces_c5_and_human_review() -> None:
    assessment = assess_complexity(
        ComplexitySignals(
            requirement_count=12,
            integration_count=6,
            non_functional_requirement_count=5,
            missing_information_count=4,
            contradiction_count=2,
            compliance_or_security_critical=True,
            data_migration_required=True,
            workflow_state_complexity=True,
            evidence_scarcity=True,
            novel_domain=True,
        )
    )

    plan = build_model_routing_plan(assessment, profile="quality_first")

    assert assessment.level == "C5"
    assert assessment.human_review_required is True
    assert plan.routes_by_stage["structure"].model == "deepseek-v4-pro"
    assert plan.routes_by_stage["structure"].effort == "max"
    assert plan.routes_by_stage["reliability"].provider == "moonshot"
    assert plan.routes_by_stage["reliability"].model == "kimi-k2.6"


def test_routing_plan_id_is_deterministic_for_same_inputs() -> None:
    assessment = assess_complexity(
        ComplexitySignals(
            requirement_count=7,
            integration_count=2,
            ambiguous_requirement_count=1,
            evidence_scarcity=True,
        )
    )

    first = build_model_routing_plan(assessment, profile="cost_first")
    second = build_model_routing_plan(assessment, profile="cost_first")

    assert first.plan_id == second.plan_id
    assert first.routes_by_stage == second.routes_by_stage
    # plan_id excludes created_at; deterministic identity does not
    # depend on wall-clock inequality.


def test_routing_plan_is_checkpoint_safe_json() -> None:
    assessment = assess_complexity(ComplexitySignals(requirement_count=5))
    plan = build_model_routing_plan(assessment)

    payload = plan.model_dump(mode="json")

    assert payload["project_complexity"]["classifier_version"]
    assert set(payload["routes_by_stage"]) == {
        "complexity",
        "structure",
        "recovery",
        "reliability",
        "proposal",
    }
    assert all(route["route_id"] for route in payload["routes_by_stage"].values())


def test_c5_contract_rejects_missing_human_review_requirement() -> None:
    with pytest.raises(ValidationError, match="C5 complexity requires human review"):
        ComplexityAssessment(
            level="C5",
            score=90,
            confidence=0.8,
            dimensions={"risk": 90},
            classifier_version="test",
            human_review_required=False,
        )


def test_dimensions_must_reconcile_to_authoritative_score() -> None:
    with pytest.raises(ValidationError, match="sum to score"):
        ComplexityAssessment(
            level="C2",
            score=30,
            confidence=0.8,
            dimensions={"scope": 20},
            classifier_version="test",
        )


def test_quality_profile_increases_bounded_cost_without_changing_complexity() -> None:
    assessment = assess_complexity(
        ComplexitySignals(requirement_count=8, integration_count=2, evidence_scarcity=True)
    )

    balanced = build_model_routing_plan(assessment, profile="balanced")
    quality = build_model_routing_plan(assessment, profile="quality_first")

    assert balanced.project_complexity == quality.project_complexity
    assert quality.routes_by_stage["structure"].cost_limit_usd > balanced.routes_by_stage[
        "structure"
    ].cost_limit_usd
    assert quality.plan_id != balanced.plan_id
