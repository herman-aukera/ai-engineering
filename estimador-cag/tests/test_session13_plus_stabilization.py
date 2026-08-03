"""Stabilization regression tests for the final Session 13 Plus gate."""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from langgraph.types import Command

from app.generation.graph.nodes.proposal import build_proposal_node
from app.generation.graph.nodes.semantic_classify import build_semantic_classify_node
from app.schemas.v3_routing import ComplexitySignals
from app.services.reviewed_graph_estimation import ReviewedGraphEstimationService
from app.services.v3_complexity_router import assess_complexity, build_model_routing_plan


class _Runner:
    def __init__(self) -> None:
        self.input_state = None
        self.config = None

    async def ainvoke(self, input, config=None):
        self.input_state = input
        self.config = config
        return {}

    async def aget_state(self, config):
        return SimpleNamespace(values=self.input_state, next=(), interrupts=())


@pytest.mark.asyncio
async def test_service_start_accepts_and_checkpoints_provider_selection() -> None:
    runner = _Runner()
    service = ReviewedGraphEstimationService(graph=runner)
    estimation_id = uuid4()
    run = await service.start(
        transcript="Build a secure reviewed estimator with enough detail for validation.",
        human_review_mode="risk_based",
        estimation_id=estimation_id,
        provider="kimi",
        reasoning="max",
        context_detail="minimal",
    )
    assert run.estimation_id == str(estimation_id)
    assert run.state["provider_selection"] == {
        "provider": "kimi",
        "reasoning": "max",
        "context_detail": "minimal",
    }


def test_live_key_sentinel_test_is_not_a_real_credential(monkeypatch) -> None:
    from tests import test_session13_plus_provider_calibration as calibration

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test")
    assert calibration._has_deepseek_key() is False


def test_authoritative_level_controls_routes_without_fabricating_assessment() -> None:
    deterministic = assess_complexity(ComplexitySignals(requirement_count=1))
    assert deterministic.level == "C1"
    plan = build_model_routing_plan(deterministic, authoritative_level="C4")
    assert plan.project_complexity.level == "C1"
    assert "complexity:C4" in plan.routes_by_stage["structure"].reason_codes
    assert plan.routes_by_stage["structure"].model == "deepseek-v4-pro"


@pytest.mark.asyncio
async def test_classifier_handover_is_command_only() -> None:
    node = build_semantic_classify_node()
    result = await node(
        {
            "transcript": "Build a simple API with authentication and database integration.",
            "errors": [],
            "trace_events": [],
        }
    )
    assert isinstance(result, Command)
    assert result.goto == "structure_phase"

    from app.generation.graph import reviewed_build

    source = inspect.getsource(reviewed_build.build_reviewed_estimation_graph)
    assert 'add_edge("semantic_classify", "structure_phase")' not in source


def test_sse_activity_projection_excludes_sensitive_state() -> None:
    from app.routers.reviewed_graph_estimations import _safe_activity_delta

    projected = _safe_activity_delta(
        "semantic_classify",
        {
            "transcript": "secret customer transcript",
            "errors": [{"message": "internal stack"}],
            "status": "pending",
            "review_required": True,
            "trace_events": [
                {
                    "event_type": "semantic_classification_completed",
                    "node": "semantic_classify",
                    "summary": "contains private rationale",
                    "evidence_refs": ["private-id"],
                    "state_delta_keys": ["status"],
                }
            ],
        },
    )
    assert projected["status"] == "pending"
    assert projected["review_required"] is True
    assert "transcript" not in projected
    assert "errors" not in projected
    event = projected["trace_events"][0]
    assert "summary" not in event
    assert "evidence_refs" not in event


def test_stream_identity_uses_one_uuid() -> None:
    from app.routers.reviewed_graph_estimations import _stream_identity

    estimation_id = uuid4()
    resolved, thread_id = _stream_identity(estimation_id)
    assert resolved == estimation_id
    assert str(estimation_id) in thread_id
    assert UUID(str(resolved)) == estimation_id


@pytest.mark.asyncio
async def test_proposal_preserves_human_review_blocker() -> None:
    node = build_proposal_node()
    update = await node(
        {
            "estimate": {"total_hours": 40.0, "total_cost_eur": 4000.0, "currency": "EUR", "components": []},
            "reliability_report": {"overall_score": 0.3, "requires_human_review": True},
            "critic_report": {"verdict": "needs_iteration"},
            "boss_decision": {"action": "human_review"},
            "arbitrated_assessment": {"arbitrated_level": "C4", "human_review_required": True},
        }
    )
    proposal = update["proposal"]
    assert proposal["human_review_required"] is True
    assert "Estimate is ready for acceptance. No blockers." not in proposal["recommendations"]
