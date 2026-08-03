from __future__ import annotations

import pytest

from app.schemas.session14_plus_policy import ModelCapabilityRegistry
from app.schemas.v3_routing import ComplexitySignals
from app.services.unified_capability_registry import (
    build_unified_capability_registry,
    load_benchmark_snapshot,
)
from app.services.unified_routing_policy import (
    build_unified_model_routing_plan,
    validate_unified_routing_plan_capabilities,
)
from app.services.v3_complexity_router import assess_complexity


def _high_complexity_assessment():
    return assess_complexity(
        ComplexitySignals(
            requirement_count=12,
            integration_count=5,
            non_functional_requirement_count=4,
            ambiguous_requirement_count=3,
            missing_information_count=3,
            contradiction_count=1,
            compliance_or_security_critical=True,
            workflow_state_complexity=True,
            evidence_scarcity=True,
        )
    )


def test_benchmark_snapshot_builds_only_evidence_backed_capabilities() -> None:
    snapshot = load_benchmark_snapshot()
    registry = build_unified_capability_registry(snapshot)

    enabled = {
        (record.provider, record.provider_model_id)
        for record in registry.records
        if record.enabled
    }

    assert ("deepseek", "deepseek-v4-flash") in enabled
    assert ("deepseek", "deepseek-v4-pro") in enabled
    assert ("moonshot", "kimi-k3") in enabled
    assert ("openai", "gpt-5.6-sol") in enabled
    assert ("python", "deterministic-recovery") in enabled
    assert ("moonshot", "kimi-k2.6") not in enabled


def test_unified_plan_authorizes_every_primary_and_fallback_route() -> None:
    registry = build_unified_capability_registry(load_benchmark_snapshot())
    plan = build_unified_model_routing_plan(
        _high_complexity_assessment(),
        profile="quality_first",
    )

    authorized = validate_unified_routing_plan_capabilities(plan, registry)

    serialized = plan.model_dump_json()
    assert "kimi-k2.6" not in serialized
    assert "kimi-k3" in serialized
    assert all(route.fallback_route_ids for route in plan.routes_by_stage.values())
    assert len(authorized) == 10
    assert any(key.startswith("structure:fallback:") for key in authorized)


def test_missing_fallback_capability_fails_closed() -> None:
    full_registry = build_unified_capability_registry(load_benchmark_snapshot())
    registry_without_moonshot = ModelCapabilityRegistry(
        registry_version="without-moonshot",
        generated_at=full_registry.generated_at,
        records=[
            record
            for record in full_registry.records
            if record.provider != "moonshot"
        ],
    )
    plan = build_unified_model_routing_plan(_high_complexity_assessment())

    with pytest.raises(ValueError, match="unregistered model route"):
        validate_unified_routing_plan_capabilities(
            plan,
            registry_without_moonshot,
        )
