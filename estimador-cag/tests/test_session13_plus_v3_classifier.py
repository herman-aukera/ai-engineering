"""Red tests for Session 13 Plus S2A: semantic-classifier contracts and deterministic fake."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# 1. SemanticSignals — provider-neutral input signals
# ---------------------------------------------------------------------------

def test_semantic_signals_are_provider_neutral() -> None:
    """SemanticSignals must not contain provider, model, or API fields."""
    from app.schemas.v3_classifier import SemanticSignals

    signals = SemanticSignals(
        domain_category="web",
        primary_modality="text",
        scope_indicators=["greenfield"],
        risk_indicators=[],
        ambiguity_flags=[],
        complexity_hints=[],
        estimated_requirement_count=5,
        estimated_integration_count=2,
        requires_specialist_review=False,
        transcript_quality="well_structured",
    )
    payload = signals.model_dump(mode="json")
    forbidden = {"provider", "model", "api_key", "api_base", "endpoint", "token"}
    assert forbidden.isdisjoint(payload.keys())


def test_semantic_signals_enforces_counts_are_non_negative() -> None:
    """Estimated counts must be >= 0."""
    from app.schemas.v3_classifier import SemanticSignals

    with pytest.raises(ValidationError):
        SemanticSignals(
            domain_category="web",
            primary_modality="text",
            estimated_requirement_count=-1,
            estimated_integration_count=0,
            transcript_quality="well_structured",
        )


def test_semantic_signals_rejects_unknown_transcript_quality() -> None:
    """transcript_quality must be a recognised value."""
    from app.schemas.v3_classifier import SemanticSignals

    with pytest.raises(ValidationError):
        SemanticSignals(
            domain_category="web",
            primary_modality="text",
            transcript_quality="invalid-quality-value",
        )


# ---------------------------------------------------------------------------
# 2. SemanticAssessment — LLM-produced classification
# ---------------------------------------------------------------------------

def test_semantic_assessment_is_checkpoint_safe_json() -> None:
    """SemanticAssessment round-trips through model_dump(mode='json')."""
    from app.schemas.v3_classifier import SemanticAssessment, SemanticSignals

    signals = SemanticSignals(
        domain_category="infra",
        primary_modality="code_heavy",
        scope_indicators=["migration"],
        risk_indicators=["data_loss"],
        complexity_hints=["distributed"],
        estimated_requirement_count=20,
        estimated_integration_count=8,
        requires_specialist_review=True,
        transcript_quality="conversational",
    )
    assessment = SemanticAssessment(
        level="C3",
        confidence=0.75,
        signals=signals,
        rationale="The transcript describes a distributed migration with data-loss risk.",
        classifier_version="session13-v3-semantic-test-1.0.0",
    )
    payload = assessment.model_dump(mode="json")
    assert payload["level"] == "C3"
    assert payload["confidence"] == 0.75
    assert payload["signals"]["domain_category"] == "infra"
    assert payload["classifier_version"] == "session13-v3-semantic-test-1.0.0"


def test_semantic_assessment_rejects_invalid_level() -> None:
    """level must be a valid C0-C5 value."""
    from app.schemas.v3_classifier import SemanticAssessment, SemanticSignals

    signals = SemanticSignals(
        domain_category="web",
        primary_modality="text",
        transcript_quality="well_structured",
    )
    with pytest.raises(ValidationError):
        SemanticAssessment(
            level="C6",  # invalid
            confidence=0.5,
            signals=signals,
            rationale="Invalid level.",
            classifier_version="test",
        )


def test_semantic_assessment_rejects_confidence_out_of_range() -> None:
    """confidence must be in [0, 1]."""
    from app.schemas.v3_classifier import SemanticAssessment, SemanticSignals

    signals = SemanticSignals(
        domain_category="web",
        primary_modality="text",
        transcript_quality="well_structured",
    )
    with pytest.raises(ValidationError):
        SemanticAssessment(
            level="C1",
            confidence=1.5,
            signals=signals,
            rationale="Invalid confidence.",
            classifier_version="test",
        )


def test_semantic_assessment_requires_classifier_version() -> None:
    """classifier_version must be a non-empty string."""
    from app.schemas.v3_classifier import SemanticAssessment, SemanticSignals

    signals = SemanticSignals(
        domain_category="web",
        primary_modality="text",
        transcript_quality="well_structured",
    )
    with pytest.raises(ValidationError):
        SemanticAssessment(
            level="C1",
            confidence=0.5,
            signals=signals,
            rationale="Missing version.",
            classifier_version="",
        )


# ---------------------------------------------------------------------------
# 3. FakeSemanticClassifier — deterministic fake for CI
# ---------------------------------------------------------------------------

def test_fake_classifier_produces_stable_output_for_same_input() -> None:
    """Same transcript and configuration must produce identical assessments."""
    from app.services.v3_semantic_classifier import FakeSemanticClassifier

    fake = FakeSemanticClassifier()
    first = fake.classify("Build a FastAPI onboarding platform with PostgreSQL.")
    second = fake.classify("Build a FastAPI onboarding platform with PostgreSQL.")
    assert first == second
    assert first.level == second.level
    assert first.confidence == second.confidence


def test_fake_classifier_records_every_call() -> None:
    """The fake must record each transcript it receives for test assertions."""
    from app.services.v3_semantic_classifier import FakeSemanticClassifier

    fake = FakeSemanticClassifier()
    assert len(fake.calls) == 0

    fake.classify("Transcript A.")
    assert len(fake.calls) == 1
    assert fake.calls[0] == "Transcript A."

    fake.classify("Transcript B.")
    assert len(fake.calls) == 2
    assert fake.calls[1] == "Transcript B."


def test_fake_classifier_returns_configured_assessment() -> None:
    """The fake must return the exact assessment it was configured with."""
    from app.schemas.v3_classifier import SemanticAssessment, SemanticSignals
    from app.services.v3_semantic_classifier import FakeSemanticClassifier

    configured_signals = SemanticSignals(
        domain_category="mobile",
        primary_modality="mixed",
        scope_indicators=["greenfield"],
        risk_indicators=["security"],
        complexity_hints=["real_time"],
        estimated_requirement_count=15,
        estimated_integration_count=4,
        requires_specialist_review=True,
        transcript_quality="well_structured",
    )
    configured = SemanticAssessment(
        level="C4",
        confidence=0.85,
        signals=configured_signals,
        rationale="Pre-configured assessment for testing.",
        classifier_version="configured-1.0.0",
    )
    fake = FakeSemanticClassifier(default_assessment=configured)

    result = fake.classify("Any transcript content.")
    assert result == configured
    assert result.level == "C4"


def test_fake_classifier_default_returns_simple_c1() -> None:
    """The default fake (no configuration) returns a low-complexity C1 for any input."""
    from app.services.v3_semantic_classifier import FakeSemanticClassifier

    fake = FakeSemanticClassifier()
    result = fake.classify("Some random transcript.")

    assert result.level == "C1"
    assert result.confidence > 0
    assert result.classifier_version.startswith("session13-v3-semantic-fake-")
    assert result.signals.domain_category == "unknown"


# ---------------------------------------------------------------------------
# 4. SemanticClassifier protocol
# ---------------------------------------------------------------------------

def test_fake_classifier_satisfies_semantic_classifier_protocol() -> None:
    """FakeSemanticClassifier must be usable wherever SemanticClassifier is expected."""
    from app.services.v3_semantic_classifier import (
        FakeSemanticClassifier,
        SemanticClassifier,
    )

    fake = FakeSemanticClassifier()
    assert isinstance(fake, SemanticClassifier)


# ---------------------------------------------------------------------------
# 5. ClassifierArbitration — deterministic vs semantic resolution
# ---------------------------------------------------------------------------

def test_arbitration_when_both_agree_returns_consensus() -> None:
    """When deterministic and semantic agree on level, use deterministic with consensus."""
    from app.schemas.v3_classifier import ClassifierArbitration, SemanticAssessment, SemanticSignals
    from app.schemas.v3_routing import ComplexityAssessment
    from app.services.v3_semantic_classifier import arbitrate_classification

    deterministic = ComplexityAssessment(
        level="C2",
        score=35,
        confidence=0.9,
        dimensions={"scope": 10, "integrations": 10, "risk": 5, "ambiguity": 5, "evidence": 3, "input": 2},
        classifier_version="deterministic-1.0.0",
    )
    semantic = SemanticAssessment(
        level="C2",
        confidence=0.8,
        signals=SemanticSignals(
            domain_category="web",
            primary_modality="text",
            transcript_quality="well_structured",
        ),
        rationale="Both agree on C2.",
        classifier_version="semantic-1.0.0",
    )
    result = arbitrate_classification(deterministic=deterministic, semantic=semantic)

    assert isinstance(result, ClassifierArbitration)
    assert result.arbitrated_level == "C2"
    assert result.resolution == "consensus"
    assert result.human_review_required is False


def test_arbitration_when_semantic_is_higher_escalates_with_reason() -> None:
    """When semantic level exceeds deterministic, escalate and record the reason."""
    from app.schemas.v3_classifier import SemanticAssessment, SemanticSignals
    from app.schemas.v3_routing import ComplexityAssessment
    from app.services.v3_semantic_classifier import arbitrate_classification

    deterministic = ComplexityAssessment(
        level="C2",
        score=35,
        confidence=0.9,
        dimensions={"scope": 15, "integrations": 5, "risk": 5, "ambiguity": 5, "evidence": 3, "input": 2},
        classifier_version="deterministic-1.0.0",
    )
    semantic = SemanticAssessment(
        level="C4",
        confidence=0.7,
        signals=SemanticSignals(
            domain_category="infra",
            primary_modality="code_heavy",
            scope_indicators=["migration"],
            risk_indicators=["data_loss"],
            complexity_hints=["distributed", "multi_team"],
            estimated_requirement_count=30,
            estimated_integration_count=10,
            transcript_quality="conversational",
        ),
        rationale="Multiple distributed teams and data migration risk suggest C4.",
        classifier_version="semantic-1.0.0",
    )
    result = arbitrate_classification(deterministic=deterministic, semantic=semantic)

    assert result.arbitrated_level == "C4"
    assert result.resolution == "semantic_escalation"
    assert len(result.resolution_reason) > 0


def test_arbitration_when_deterministic_is_higher_overrides_semantic() -> None:
    """Deterministic structural evidence overrides a lower semantic assessment."""
    from app.schemas.v3_classifier import SemanticAssessment, SemanticSignals
    from app.schemas.v3_routing import ComplexityAssessment
    from app.services.v3_semantic_classifier import arbitrate_classification

    deterministic = ComplexityAssessment(
        level="C4",
        score=70,
        confidence=0.85,
        dimensions={"scope": 20, "integrations": 15, "risk": 15, "ambiguity": 10, "evidence": 5, "input": 5},
        classifier_version="deterministic-1.0.0",
    )
    semantic = SemanticAssessment(
        level="C1",
        confidence=0.9,
        signals=SemanticSignals(
            domain_category="web",
            primary_modality="text",
            transcript_quality="well_structured",
        ),
        rationale="Looks simple to me.",
        classifier_version="semantic-1.0.0",
    )
    result = arbitrate_classification(deterministic=deterministic, semantic=semantic)

    assert result.arbitrated_level == "C4"
    assert result.resolution == "deterministic_override"
    assert len(result.resolution_reason) > 0


def test_arbitration_forces_human_review_when_semantic_flags_security() -> None:
    """Semantic risk indicators for security or compliance force human review."""
    from app.schemas.v3_classifier import SemanticAssessment, SemanticSignals
    from app.schemas.v3_routing import ComplexityAssessment
    from app.services.v3_semantic_classifier import arbitrate_classification

    deterministic = ComplexityAssessment(
        level="C2",
        score=30,
        confidence=0.9,
        dimensions={"scope": 10, "integrations": 5, "risk": 5, "ambiguity": 5, "evidence": 3, "input": 2},
        classifier_version="deterministic-1.0.0",
    )
    semantic = SemanticAssessment(
        level="C2",
        confidence=0.7,
        signals=SemanticSignals(
            domain_category="web",
            primary_modality="text",
            risk_indicators=["security", "compliance"],
            transcript_quality="well_structured",
        ),
        rationale="Security and compliance risks present.",
        classifier_version="semantic-1.0.0",
    )
    result = arbitrate_classification(deterministic=deterministic, semantic=semantic)

    assert result.human_review_required is True
    assert result.arbitrated_level == "C2"


def test_arbitration_preserves_deterministic_c5_always() -> None:
    """Deterministic C5 must survive regardless of what the semantic classifier claims."""
    from app.schemas.v3_classifier import SemanticAssessment, SemanticSignals
    from app.schemas.v3_routing import ComplexityAssessment
    from app.services.v3_semantic_classifier import arbitrate_classification

    deterministic = ComplexityAssessment(
        level="C5",
        score=90,
        confidence=0.8,
        dimensions={"scope": 20, "integrations": 20, "risk": 20, "ambiguity": 10, "evidence": 10, "input": 10},
        classifier_version="deterministic-1.0.0",
        human_review_required=True,
    )
    semantic = SemanticAssessment(
        level="C1",
        confidence=0.95,
        signals=SemanticSignals(
            domain_category="web",
            primary_modality="text",
            transcript_quality="well_structured",
        ),
        rationale="Looks trivial.",
        classifier_version="semantic-1.0.0",
    )
    result = arbitrate_classification(deterministic=deterministic, semantic=semantic)

    assert result.arbitrated_level == "C5"
    assert result.human_review_required is True
    assert result.resolution == "deterministic_override"


def test_arbitration_result_is_checkpoint_safe_json() -> None:
    """ClassifierArbitration round-trips through model_dump(mode='json')."""
    from app.schemas.v3_classifier import SemanticAssessment, SemanticSignals
    from app.schemas.v3_routing import ComplexityAssessment
    from app.services.v3_semantic_classifier import arbitrate_classification

    deterministic = ComplexityAssessment(
        level="C3",
        score=50,
        confidence=0.85,
        dimensions={"scope": 15, "integrations": 10, "risk": 5, "ambiguity": 10, "evidence": 5, "input": 5},
        classifier_version="deterministic-1.0.0",
    )
    semantic = SemanticAssessment(
        level="C4",
        confidence=0.65,
        signals=SemanticSignals(
            domain_category="mobile",
            primary_modality="mixed",
            scope_indicators=["greenfield"],
            risk_indicators=["security"],
            complexity_hints=["real_time"],
            transcript_quality="conversational",
        ),
        rationale="Mobile real-time app with security concerns.",
        classifier_version="semantic-1.0.0",
    )
    result = arbitrate_classification(deterministic=deterministic, semantic=semantic)
    payload = result.model_dump(mode="json")

    assert payload["arbitrated_level"] == "C4"
    assert payload["resolution"] == "semantic_escalation"
    assert isinstance(payload["resolution_reason"], str)
    assert payload["human_review_required"] is True
    assert payload["deterministic_assessment_ref"] == "deterministic-1.0.0"
    assert payload["semantic_assessment_ref"] == "semantic-1.0.0"


def test_arbitration_rejects_mismatched_policy_prefix() -> None:
    """When classifier versions have incompatible policy prefixes, raise ValueError."""
    from app.schemas.v3_classifier import SemanticAssessment, SemanticSignals
    from app.schemas.v3_routing import ComplexityAssessment
    from app.services.v3_semantic_classifier import arbitrate_classification

    deterministic = ComplexityAssessment(
        level="C2",
        score=30,
        confidence=0.9,
        dimensions={"scope": 10, "integrations": 5, "risk": 5, "ambiguity": 5, "evidence": 3, "input": 2},
        classifier_version="session13-v3-deterministic-features-1.0.0",
    )
    semantic = SemanticAssessment(
        level="C2",
        confidence=0.8,
        signals=SemanticSignals(
            domain_category="web",
            primary_modality="text",
            transcript_quality="well_structured",
        ),
        rationale="Agree on C2.",
        classifier_version="session14-v4-semantic-experimental-0.1.0",
    )
    with pytest.raises(ValueError, match="policy"):
        arbitrate_classification(deterministic=deterministic, semantic=semantic)


# ---------------------------------------------------------------------------
# 5a. R2a — authoritative route plan reflects arbitrated level
# ---------------------------------------------------------------------------

def test_route_plan_reflects_arbitrated_level_not_deterministic() -> None:
    """When arbitration escalates, the route plan must use the arbitrated level."""
    from app.schemas.v3_classifier import SemanticAssessment, SemanticSignals
    from app.schemas.v3_routing import ComplexityAssessment
    from app.services.v3_complexity_router import build_model_routing_plan
    from app.services.v3_semantic_classifier import arbitrate_classification

    # Deterministic says C2, semantic says C4 → arbitrated is C4.
    deterministic = ComplexityAssessment(
        level="C2", score=35, confidence=0.9,
        dimensions={"scope": 15, "integrations": 5, "risk": 5, "ambiguity": 5, "evidence": 3, "input": 2},
        classifier_version="deterministic-1.0.0",
    )
    semantic = SemanticAssessment(
        level="C4", confidence=0.75,
        signals=SemanticSignals(domain_category="infra", primary_modality="code_heavy",
                                transcript_quality="conversational",
                                risk_indicators=["data_loss"],
                                complexity_hints=["distributed"]),
        rationale="Distributed migration with data-loss risk.",
        classifier_version="semantic-1.0.0",
    )
    arbitrated = arbitrate_classification(deterministic=deterministic, semantic=semantic)
    assert arbitrated.arbitrated_level == "C4"

    # Build a route plan from the arbitrated level, not the deterministic.
    arbitrated_assessment = ComplexityAssessment(
        level=arbitrated.arbitrated_level, score=deterministic.score,
        confidence=deterministic.confidence, dimensions=deterministic.dimensions,
        classifier_version=deterministic.classifier_version,
        human_review_required=arbitrated.human_review_required,
    )
    plan = build_model_routing_plan(arbitrated_assessment)
    # C4 structure route uses deepseek-v4-pro, not flash.
    assert plan.routes_by_stage["structure"].model == "deepseek-v4-pro"


# ---------------------------------------------------------------------------
# 5b. R2b — arbitration safety: low confidence and disagreement gates
# ---------------------------------------------------------------------------

def test_low_confidence_semantic_forces_deterministic_override() -> None:
    """When semantic confidence < 0.6, the deterministic level must dominate."""
    from app.schemas.v3_classifier import SemanticAssessment, SemanticSignals
    from app.schemas.v3_routing import ComplexityAssessment
    from app.services.v3_semantic_classifier import arbitrate_classification

    deterministic = ComplexityAssessment(
        level="C2", score=35, confidence=0.9,
        dimensions={"scope": 10, "integrations": 5, "risk": 5, "ambiguity": 5, "evidence": 5, "input": 5},
        classifier_version="deterministic-1.0.0",
    )
    semantic = SemanticAssessment(
        level="C5", confidence=0.45,  # Low confidence
        signals=SemanticSignals(domain_category="web", primary_modality="text",
                                transcript_quality="well_structured"),
        rationale="Might be very complex, but I'm not sure.",
        classifier_version="semantic-1.0.0",
    )
    result = arbitrate_classification(deterministic=deterministic, semantic=semantic)
    # Low-confidence semantic C5 must NOT escalate.
    assert result.arbitrated_level == "C2"
    assert result.resolution == "deterministic_override"
    assert "low confidence" in result.resolution_reason.lower()


def test_disagreement_greater_than_one_level_forces_human_review() -> None:
    """When semantic and deterministic disagree by > 1 C-level, human review is required."""
    from app.schemas.v3_classifier import SemanticAssessment, SemanticSignals
    from app.schemas.v3_routing import ComplexityAssessment
    from app.services.v3_semantic_classifier import arbitrate_classification

    deterministic = ComplexityAssessment(
        level="C1", score=15, confidence=0.9,
        dimensions={"scope": 5, "integrations": 5, "risk": 0, "ambiguity": 0, "evidence": 3, "input": 2},
        classifier_version="deterministic-1.0.0",
    )
    semantic = SemanticAssessment(
        level="C4", confidence=0.85,  # Confident but 3 levels above
        signals=SemanticSignals(domain_category="infra", primary_modality="code_heavy",
                                transcript_quality="conversational"),
        rationale="This is a complex distributed system.",
        classifier_version="semantic-1.0.0",
    )
    result = arbitrate_classification(deterministic=deterministic, semantic=semantic)
    # Disagreement > 1 level must force human review.
    assert result.human_review_required is True
    assert "disagreement" in result.resolution_reason.lower()


def test_arbitration_stable_reason_codes_are_machine_readable() -> None:
    """Resolution values must be stable enum-like strings for checkpoint safety."""
    from app.schemas.v3_classifier import SemanticAssessment, SemanticSignals
    from app.schemas.v3_routing import ComplexityAssessment
    from app.services.v3_semantic_classifier import arbitrate_classification

    deterministic = ComplexityAssessment(
        level="C3", score=50, confidence=0.85,
        dimensions={"scope": 15, "integrations": 10, "risk": 5, "ambiguity": 10, "evidence": 5, "input": 5},
        classifier_version="deterministic-1.0.0",
    )
    semantic = SemanticAssessment(
        level="C5", confidence=0.9,
        signals=SemanticSignals(domain_category="infra", primary_modality="mixed",
                                risk_indicators=["security"],
                                transcript_quality="well_structured"),
        rationale="Security-critical infrastructure.",
        classifier_version="semantic-1.0.0",
    )
    result = arbitrate_classification(deterministic=deterministic, semantic=semantic)
    # Resolution must be one of the three stable values.
    assert result.resolution in {"consensus", "semantic_escalation", "deterministic_override"}
    assert len(result.resolution_reason) > 0
    assert isinstance(result.resolution_reason, str)


# ---------------------------------------------------------------------------
# 6. Semantic classify graph node — isolated from the full graph
# ---------------------------------------------------------------------------

# NOTE: Tests use plain dicts matching the ReviewedEstimationGraphState
# TypedDict shape rather than importing the TypedDict, avoiding a transitive
# import of app.config.settings which requires API keys at module level.

def _state(**overrides: object) -> dict[str, object]:
    """Minimal reviewed-graph state dict for classifier node tests."""
    state: dict[str, object] = {
        "transcript": "Build a secure FastAPI onboarding platform.",
        "estimation_id": "11111111-1111-4111-8111-111111111111",
        "graph_version": "session13.plus.v1",
        "trace_events": [],
    }
    state.update(overrides)
    return state


def test_semantic_classify_node_can_be_imported() -> None:
    """The node builder module must exist and export the builder."""
    from app.generation.graph.nodes.semantic_classify import (
        build_semantic_classify_node,
    )

    assert callable(build_semantic_classify_node)


@pytest.mark.asyncio
async def test_semantic_classify_node_stores_semantic_assessment() -> None:
    """The node must call the fake classifier and store the result in state."""
    from app.generation.graph.nodes.semantic_classify import build_semantic_classify_node

    state = _state(reformulated_request="Project type: web\nRequest: Build a secure FastAPI onboarding platform.")

    node = build_semantic_classify_node()
    update = await node(state)

    assert "semantic_assessment" in update
    assert update["semantic_assessment"]["level"] == "C1"
    assert "v3_complexity" in update
    assert "arbitrated_assessment" in update
    assert "v3_route_plan" in update
    assert len(update["trace_events"]) >= 1


@pytest.mark.asyncio
async def test_semantic_classify_node_uses_reformulated_request() -> None:
    """When reformulated_request is present the node must prefer it over transcript."""
    from app.generation.graph.nodes.semantic_classify import build_semantic_classify_node

    state = _state(
        transcript="IGNORED raw input.",
        reformulated_request=(
            "Project type: infra\n"
            "Request: Migrate PostgreSQL cluster with zero downtime.\n"
            "Constraints: PostgreSQL; No data loss\n"
            "Acceptance criteria: Resume after restart"
        ),
        estimation_id="11111111-1111-4111-8111-111111111112",
    )

    node = build_semantic_classify_node()
    update = await node(state)

    assert update["v3_complexity"] is not None
    assert "semantic_assessment" in update


@pytest.mark.asyncio
async def test_semantic_classify_node_produces_arbitrated_assessment() -> None:
    """The node must run arbitration and store the resolved assessment."""
    from app.generation.graph.nodes.semantic_classify import build_semantic_classify_node

    state = _state(
        transcript="Build a simple web app.",
        estimation_id="11111111-1111-4111-8111-111111111113",
    )

    node = build_semantic_classify_node()
    update = await node(state)

    arb = update["arbitrated_assessment"]
    assert "arbitrated_level" in arb
    assert "resolution" in arb
    assert "human_review_required" in arb
    # Fake returns C1; deterministic baseline is C0 for a bare one-liner → escalation
    assert arb["resolution"] == "semantic_escalation"


@pytest.mark.asyncio
async def test_semantic_classify_node_stores_route_plan() -> None:
    """The node must compute and store a V3 route plan from the arbitrated assessment."""
    from app.generation.graph.nodes.semantic_classify import build_semantic_classify_node

    state = _state(estimation_id="11111111-1111-4111-8111-111111111114")

    node = build_semantic_classify_node()
    update = await node(state)

    plan = update["v3_route_plan"]
    assert "plan_id" in plan
    assert "routes_by_stage" in plan
    assert set(plan["routes_by_stage"]) == {
        "complexity", "structure", "recovery", "reliability", "proposal",
    }


@pytest.mark.asyncio
async def test_semantic_classify_node_emits_domain_trace_events() -> None:
    """Every execution must emit trace events recording what happened."""
    from app.generation.graph.nodes.semantic_classify import build_semantic_classify_node

    state = _state(
        transcript="Build a web app.",
        estimation_id="11111111-1111-4111-8111-111111111115",
    )

    node = build_semantic_classify_node()
    update = await node(state)

    events = update["trace_events"]
    event_types = [e["event_type"] for e in events]
    assert "semantic_classification_completed" in event_types
    for event in events:
        assert event["node"] == "semantic_classify"


@pytest.mark.asyncio
async def test_semantic_classify_node_handles_missing_transcript_gracefully() -> None:
    """When no transcript is available the node must emit an error event, not crash."""
    from app.generation.graph.nodes.semantic_classify import build_semantic_classify_node

    state = _state(
        transcript="",
        estimation_id="11111111-1111-4111-8111-111111111116",
    )
    state.pop("transcript", None)

    node = build_semantic_classify_node()
    update = await node(state)

    assert update["review_required"] is True
    errors = update.get("errors", [])
    assert any(e["code"] == "missing_transcript_for_classification" for e in errors)


# ---------------------------------------------------------------------------
# 7. Reviewed-graph integration — classifier node wired into the full graph
# ---------------------------------------------------------------------------

# These tests use fakes for all graph dependencies and an in-memory
# checkpointer.  No real model, network, or database calls are made.


class _FakeExtractor:
    async def extract_requirements(self, *, transcript: str):
        assert transcript
        return [
            {"requirement_id": "req-1", "text": "Authenticate users with JWT."},
            {"requirement_id": "req-2", "text": "Persist accounts in PostgreSQL."},
        ]


class _FakeClassifier:
    async def classify_components(self, *, requirements):
        return [
            {
                "component_id": "cmp-auth",
                "name": "Authentication",
                "category": "backend",
                "requirement_ids": ["req-1", "req-2"],
            }
        ]


class _FakeSearcher:
    async def search_budgets(self, *, component, k: int):
        return [
            {
                "component_id": "cmp-auth",
                "budget_id": "BUD-101",
                "reference_component_id": "REF-1",
                "source_document_id": "DOC-10",
                "source_chunk_id": "CH-101",
                "recorded_hours": 40.0,
                "distance": 0.08,
                "score": 0.92,
                "retrieval_method": "deterministic_fake",
            },
            {
                "component_id": "cmp-auth",
                "budget_id": "BUD-202",
                "reference_component_id": "REF-2",
                "source_document_id": "DOC-20",
                "source_chunk_id": "CH-202",
                "recorded_hours": 40.0,
                "distance": 0.1,
                "score": 0.9,
                "retrieval_method": "deterministic_fake",
            },
        ]


def _graph_deps() -> object:
    from app.generation.graph.ports import GraphNodeDependencies
    return GraphNodeDependencies(
        requirement_extractor=_FakeExtractor(),
        component_classifier=_FakeClassifier(),
        budget_searcher=_FakeSearcher(),
    )


def _initial_reviewed_state() -> dict[str, object]:
    return {
        "transcript": "Build a secure FastAPI onboarding platform with PostgreSQL.",
        "estimation_id": "11111111-1111-4111-8111-111111111200",
        "graph_version": "session13.plus.v1",
        "human_review_mode": "disabled",
        "structure_review_revision": 0,
        "execution_budgets": {
            "retry_count": 0, "retry_limit": 2,
            "fallback_count": 0, "fallback_limit": 1,
            "tool_call_count": 0, "tool_call_limit": 8,
            "elapsed_ms": 0, "latency_budget_ms": 120000,
            "estimated_cost_usd": 0.0, "cost_budget_usd": 1.0,
        },
    }


@pytest.mark.asyncio
async def test_reviewed_graph_stores_classifier_results_in_final_state() -> None:
    """After a full run the state must contain semantic_assessment and friends."""
    from langgraph.checkpoint.memory import InMemorySaver

    from app.generation.graph.reviewed_build import build_reviewed_estimation_graph

    graph = build_reviewed_estimation_graph(_graph_deps(), checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "s2d-classifier-results"}}

    result = await graph.ainvoke(_initial_reviewed_state(), config=config)

    assert "semantic_assessment" in result
    assert result["semantic_assessment"]["level"] == "C1"
    assert "v3_complexity" in result
    assert "arbitrated_assessment" in result
    assert "v3_route_plan" in result
    assert "plan_id" in result["v3_route_plan"]


@pytest.mark.asyncio
async def test_reviewed_graph_completes_estimation_with_classifier() -> None:
    """The graph must still produce a valid estimate after the classifier runs."""
    from langgraph.checkpoint.memory import InMemorySaver

    from app.generation.graph.reviewed_build import build_reviewed_estimation_graph

    graph = build_reviewed_estimation_graph(_graph_deps(), checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "s2d-estimation-completes"}}

    result = await graph.ainvoke(_initial_reviewed_state(), config=config)

    assert result["status"] == "validated"
    assert result["estimate"]["total_hours"] == 40.0
    assert result["critic_report"]["verdict"] == "accept"
    assert result["boss_decision"]["action"] == "accept"


@pytest.mark.asyncio
async def test_reviewed_graph_trace_includes_classifier_node() -> None:
    """The trace events must include the semantic_classify node."""
    from langgraph.checkpoint.memory import InMemorySaver

    from app.generation.graph.reviewed_build import build_reviewed_estimation_graph

    graph = build_reviewed_estimation_graph(_graph_deps(), checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "s2d-trace"}}

    result = await graph.ainvoke(_initial_reviewed_state(), config=config)

    trace_nodes = [e["node"] for e in result["trace_events"]]
    assert "semantic_classify" in trace_nodes
    assert "extract_requirements" in trace_nodes


@pytest.mark.asyncio
async def test_reviewed_graph_still_supports_structure_gate_with_classifier() -> None:
    """The graph must still pause at structure_review when review_mode='required'."""
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import Command

    from app.generation.graph.reviewed_build import build_reviewed_estimation_graph

    graph = build_reviewed_estimation_graph(_graph_deps(), checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "s2d-structure-gate"}}
    state = _initial_reviewed_state()
    state["human_review_mode"] = "required"
    state["estimation_id"] = "11111111-1111-4111-8111-111111111201"

    interrupted = await graph.ainvoke(state, config=config)
    interrupts = interrupted.get("__interrupt__", ())
    assert len(interrupts) == 1
    assert interrupts[0].value["gate"] == "structure_review"

    # Resume and verify classifier results survive the interrupt cycle.
    resumed = await graph.ainvoke(
        Command(resume={"action": "approve", "expected_revision": 0}),
        config=config,
    )
    assert "semantic_assessment" in resumed
    assert resumed["semantic_assessment"]["level"] == "C1"


# ---------------------------------------------------------------------------
# 8. V1/V2 compatibility and replay — mandatory graph is untouched
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mandatory_v1_v2_graph_still_runs_independently() -> None:
    """The mandatory 5-node graph must still compile and run with fakes."""
    from app.generation.graph.build import build_estimation_graph
    from app.generation.graph.state import new_estimation_graph_state

    graph = build_estimation_graph(_graph_deps())
    state = new_estimation_graph_state(
        transcript="Build a secure FastAPI onboarding platform with PostgreSQL.",
        estimation_id="22222222-2222-4222-8222-222222222222",
    )
    result = await graph.ainvoke(state)

    assert result["status"] == "validated"
    assert result["estimate"]["total_hours"] == 40.0


@pytest.mark.asyncio
async def test_mandatory_v1_v2_state_excludes_classifier_fields() -> None:
    """Classifier fields must not leak into the mandatory EstimationGraphState."""
    from app.generation.graph.build import build_estimation_graph
    from app.generation.graph.state import new_estimation_graph_state

    graph = build_estimation_graph(_graph_deps())
    state = new_estimation_graph_state(
        transcript="Build a web app.",
        estimation_id="22222222-2222-4222-8222-222222222223",
    )
    result = await graph.ainvoke(state)

    classifier_keys = {
        "semantic_assessment",
        "v3_complexity",
        "arbitrated_assessment",
        "v3_route_plan",
    }
    assert classifier_keys.isdisjoint(result.keys())


@pytest.mark.asyncio
async def test_reviewed_graph_replay_is_deterministic() -> None:
    """Two runs with the same inputs must produce identical state."""
    from langgraph.checkpoint.memory import InMemorySaver

    from app.generation.graph.reviewed_build import build_reviewed_estimation_graph

    first = build_reviewed_estimation_graph(_graph_deps(), checkpointer=InMemorySaver())
    second = build_reviewed_estimation_graph(_graph_deps(), checkpointer=InMemorySaver())

    config_a = {"configurable": {"thread_id": "s2e-replay-a"}}
    config_b = {"configurable": {"thread_id": "s2e-replay-b"}}

    result_a = await first.ainvoke(_initial_reviewed_state(), config=config_a)
    result_b = await second.ainvoke(_initial_reviewed_state(), config=config_b)

    assert result_a["semantic_assessment"] == result_b["semantic_assessment"]
    assert result_a["v3_complexity"] == result_b["v3_complexity"]
    assert result_a["arbitrated_assessment"] == result_b["arbitrated_assessment"]
    # Route plan: everything except created_at must be identical.
    assert result_a["v3_route_plan"]["plan_id"] == result_b["v3_route_plan"]["plan_id"]
    assert result_a["v3_route_plan"]["routes_by_stage"] == result_b["v3_route_plan"]["routes_by_stage"]
    assert result_a["v3_route_plan"]["profile"] == result_b["v3_route_plan"]["profile"]
    assert result_a["estimate"] == result_b["estimate"]


@pytest.mark.asyncio
async def test_reviewed_graph_replay_with_same_thread_is_idempotent() -> None:
    """Resuming the same thread without new input must not mutate state."""
    from langgraph.checkpoint.memory import InMemorySaver

    from app.generation.graph.reviewed_build import build_reviewed_estimation_graph

    graph = build_reviewed_estimation_graph(_graph_deps(), checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "s2e-replay-same"}}

    first = await graph.ainvoke(_initial_reviewed_state(), config=config)
    # Reading state without new input must return the same values.
    snapshot = await graph.aget_state(config)
    assert snapshot.values["semantic_assessment"] == first["semantic_assessment"]
    assert snapshot.values["estimate"] == first["estimate"]


def test_mandatory_graph_still_uses_only_five_original_nodes() -> None:
    """The mandatory graph must contain only the 5 required node names."""
    from app.generation.graph.build import REQUIRED_NODE_NAMES

    assert set(REQUIRED_NODE_NAMES) == {
        "extract_requirements",
        "classify_components",
        "search_budgets",
        "generate_estimate",
        "validate_and_consolidate",
    }
    # The mandatory graph must NOT include semantic_classify.
    assert "semantic_classify" not in REQUIRED_NODE_NAMES
