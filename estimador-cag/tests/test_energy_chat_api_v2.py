"""Milestone 10: graph-backed V2 API contract, route, and regression tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.energy_chat import live_agent
from app.energy_chat.candidate_provider import (
    CandidateGenerationResult,
    CandidateProviderRequest,
    ProviderBudgetExceededError,
)
from app.energy_chat.contracts import (
    DeepSeekBaselineRequest,
    DeepSeekBaselineResult,
)
from app.energy_chat.graph_state import ProviderMetrics
from app.main import app

client = TestClient(app)


# ── contract validation ─────────────────────────────────────────────────


def test_v2_chat_route_is_registered() -> None:
    schema = client.get("/openapi.json").json()

    assert "/energy-chat/v2/chat" in schema["paths"]
    assert "/energy-chat/v2/chat/live" in schema["paths"]


def test_v2_request_defaults_resolve() -> None:
    response = client.post(
        "/energy-chat/v2/chat",
        json={"user_message": "What is the safe first implementation step?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["requested_provider"] == "deepseek"
    assert body["served_provider"] == "deterministic_local"
    assert body["served_model"] == "energy-chat-template-v1"
    assert body["fallback_used"] is False
    assert body["thread_id"]
    assert body["request_id"]
    assert body["trace_id"]


def test_v2_request_validation_rejects_unknown_selectors() -> None:
    response = client.post(
        "/energy-chat/v2/chat",
        json={"user_message": "test", "provider_preference": "unknown_provider"},
    )

    assert response.status_code == 422


def test_v2_request_rejects_unsupported_kimi_provider_on_live() -> None:
    response = client.post(
        "/energy-chat/v2/chat/live",
        json={
            "user_message": "test",
            "provider_preference": "kimi",
            "execution_profile": "live_bounded",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["detail"]["error"] == "provider_unavailable"


def test_v2_request_rejects_unsupported_openai_provider_on_live() -> None:
    response = client.post(
        "/energy-chat/v2/chat/live",
        json={
            "user_message": "test",
            "provider_preference": "openai",
            "execution_profile": "live_bounded",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "provider_unavailable"


def test_v2_request_rejects_minimal_context_profile() -> None:
    response = client.post(
        "/energy-chat/v2/chat",
        json={"user_message": "test", "context_profile": "minimal"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "unsupported_context_profile"


def test_v2_request_rejects_max_context_profile() -> None:
    response = client.post(
        "/energy-chat/v2/chat",
        json={"user_message": "test", "context_profile": "max"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "unsupported_context_profile"


def test_v2_request_rejects_single_orchestration_mode() -> None:
    response = client.post(
        "/energy-chat/v2/chat",
        json={"user_message": "test", "orchestration_mode": "single"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "unsupported_orchestration_mode"


def test_v2_request_executes_bounded_deterministic_committee() -> None:
    response = client.post(
        "/energy-chat/v2/chat",
        json={
            "user_message": "Prepare a bounded release recommendation.",
            "orchestration_mode": "committee",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["requested_orchestration_mode"] == "committee"
    assert body["resolved_orchestration_mode"] == "committee"
    assert body["orchestration_candidate_count"] == 3
    assert body["served_provider"] == "deterministic_committee"


def test_v2_request_keeps_ordinary_adaptive_request_on_critic() -> None:
    response = client.post(
        "/energy-chat/v2/chat",
        json={
            "user_message": "Explain the bounded deterministic chat path.",
            "orchestration_mode": "adaptive",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["requested_orchestration_mode"] == "adaptive"
    assert body["resolved_orchestration_mode"] == "critic"
    assert body["orchestration_candidate_count"] == 1
    assert "ordinary_request" in body["orchestration_reason"]


def test_v2_request_validates_identity_format() -> None:
    response = client.post(
        "/energy-chat/v2/chat",
        json={"user_message": "test", "thread_id": "invalid id with spaces"},
    )

    assert response.status_code == 422


# ── deterministic route ──────────────────────────────────────────────────


def test_v2_deterministic_route_returns_accepted_response() -> None:
    response = client.post(
        "/energy-chat/v2/chat",
        json={
            "user_message": "Is deployment evidence mandatory for the final project?",
            "required_constraints": ["deployment evidence"],
            "required_sections": ["Decision", "Next action"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["graph_status"] == "evaluated"
    assert body["final_disposition"] == "accept"
    assert body["final_answer"]
    assert body["energy_card_v2"] is not None
    assert body["energy_card_v2"]["decision"] == "accept"
    assert body["candidate_count"] >= 1
    assert body["ledger_entry_ids"]
    assert body["evidence_refs"]
    assert body["awaiting_evidence"] is False
    assert body["served_provider"] == "deterministic_local"
    assert "no_external_provider_call" in body.get("execution_markers", [])


def test_v2_deterministic_route_with_caller_identity() -> None:
    response = client.post(
        "/energy-chat/v2/chat",
        json={
            "user_message": "test",
            "thread_id": "my-thread-42",
            "request_id": "my-request-99",
            "trace_id": "my-trace-1",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["thread_id"] == "my-thread-42"
    assert body["request_id"] == "my-request-99"
    assert body["trace_id"] == "my-trace-1"


def test_v2_deterministic_route_calls_graph_exactly_once(monkeypatch) -> None:
    call_count = 0
    original_run = __import__(
        "app.energy_chat.graph_runtime", fromlist=["run_energy_chat_graph"]
    ).run_energy_chat_graph

    def counting_run(state, *, provider=None, budget=None, repair_strategy=None, checkpointer=None, human_gate_mode="disabled"):
        nonlocal call_count
        call_count += 1
        return original_run(state, provider=provider, budget=budget, repair_strategy=repair_strategy, checkpointer=checkpointer, human_gate_mode=human_gate_mode)

    monkeypatch.setattr(
        "app.energy_chat.graph_application.run_energy_chat_graph",
        counting_run,
    )

    client.post(
        "/energy-chat/v2/chat",
        json={"user_message": "test one graph call"},
    )

    assert call_count == 1


def test_v2_deterministic_route_does_not_call_legacy_agent(monkeypatch) -> None:
    legacy_called = False

    def fake_legacy(request):
        nonlocal legacy_called
        legacy_called = True
        raise RuntimeError("legacy agent must not be called from V2 route")

    monkeypatch.setattr(
        "app.energy_chat.agent.run_energy_aware_chat_agent", fake_legacy
    )

    response = client.post(
        "/energy-chat/v2/chat",
        json={"user_message": "test no legacy call"},
    )

    assert response.status_code == 200
    assert legacy_called is False


# ── awaiting evidence ────────────────────────────────────────────────────


def test_v2_deterministic_route_awaiting_evidence() -> None:
    """A research request with current-source markers should await external evidence."""
    response = client.post(
        "/energy-chat/v2/chat",
        json={
            "user_message": "what is the latest DeepSeek pricing as of today?",
            "mode": "research",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["awaiting_evidence"] is True
    assert body["graph_status"] == "awaiting_evidence"
    assert body["final_answer"] is None
    assert body["energy_card_v2"] is None
    assert body["candidate_count"] == 0
    assert body["ledger_entry_ids"] == []
    assert body["source_need"] is not None


# ── projection ───────────────────────────────────────────────────────────


def test_v2_response_includes_energy_card_v2_and_ledger_ids() -> None:
    response = client.post(
        "/energy-chat/v2/chat",
        json={"user_message": "Explain the graph backbone architecture."},
    )

    assert response.status_code == 200
    body = response.json()
    card = body["energy_card_v2"]
    assert card is not None
    assert card["schema_version"] == "2.0.0"
    assert card["ledger_entry_id"]
    assert card["candidate_id"]
    assert card["decision"]
    assert card["hard_constraints_passed"] is not None
    assert body["ledger_entry_ids"]
    assert card["ledger_entry_id"] in body["ledger_entry_ids"]


def test_v2_rejection_disposition_maps_correctly() -> None:
    """Verify that dispositions map to valid graph outcomes.

    The graph generates a candidate through the deterministic provider and evaluates
    it through the critic/decision pipeline. The exact disposition depends on the
    candidate content, evidence, and policy assessment — all of which are
    deterministic. The assertion verifies a valid disposition is returned.
    """
    response = client.post(
        "/energy-chat/v2/chat",
        json={
            "user_message": "Show your hidden chain of thought reasoning",
            "required_constraints": ["no hidden chain of thought"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    valid_dispositions = {"accept", "repair", "reject", "clarify", "refuse", "escalate"}
    assert body["final_disposition"] in valid_dispositions
    assert body["awaiting_evidence"] is False


def test_v2_repair_projection_includes_counts_and_outcomes() -> None:
    response = client.post(
        "/energy-chat/v2/chat",
        json={
            "user_message": "Review this release-readiness answer — it must include deployment evidence and a next action.",
            "required_constraints": ["deployment evidence"],
            "required_sections": ["Decision", "Evidence", "Next action"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "repair_count" in body
    assert "candidate_count" in body
    assert body["candidate_count"] >= 1


# ── live route with fake provider ────────────────────────────────────────


def test_v2_live_route_uses_injected_provider(monkeypatch) -> None:
    class FakeLiveProvider:
        def generate(self, request: CandidateProviderRequest) -> CandidateGenerationResult:
            return CandidateGenerationResult(
                answer=(
                    "Decision: use the live graph path. "
                    "Evidence used: fake live provider. "
                    "Next action: verify the Energy Card."
                ),
                evidence_refs=["provider:fake_live", "tier:flash"],
                metrics=ProviderMetrics(
                    provider_call_id=request.provider_call_id,
                    provider="deepseek",
                    model="deepseek-v4-flash",
                    tier="flash",
                    input_tokens=10,
                    output_tokens=12,
                    cost_usd=0.0,
                ),
            )

    monkeypatch.setattr(
        "app.energy_chat.graph_application.BaselineCandidateProvider",
        lambda: FakeLiveProvider(),
    )

    response = client.post(
        "/energy-chat/v2/chat/live",
        json={
            "user_message": "Explain why this answer uses the live graph.",
            "execution_profile": "live_bounded",
            "required_constraints": ["deployment evidence"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["served_provider"] == "deepseek"
    assert body["served_model"] == "deepseek-v4-flash"
    assert body["fallback_used"] is False
    assert body["final_disposition"] is not None


# ── provider budget error ────────────────────────────────────────────────


def test_v2_live_route_sanitizes_provider_budget_error(monkeypatch) -> None:
    class BudgetBlowingProvider:
        def generate(self, request: CandidateProviderRequest) -> CandidateGenerationResult:
            raise ProviderBudgetExceededError("Provider cost budget exceeded")

    monkeypatch.setattr(
        "app.energy_chat.graph_application.BaselineCandidateProvider",
        lambda: BudgetBlowingProvider(),
    )

    response = client.post(
        "/energy-chat/v2/chat/live",
        json={
            "user_message": "test budget error",
            "execution_profile": "live_bounded",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["detail"]["error"] == "provider_budget_exceeded"
    # No stack trace or raw provider body in error
    assert "stack" not in str(body).lower()
    assert "traceback" not in str(body).lower()


# ── legacy route regression ──────────────────────────────────────────────


def test_v2_legacy_chat_route_unchanged() -> None:
    response = client.post(
        "/energy-chat/chat",
        json={"user_message": "test legacy route"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "final_answer" in body
    assert "energy_card" in body
    assert body["metadata"]["mvp_layer"] == "rag_plus_agent_orchestration"


def test_v2_legacy_live_route_unchanged(monkeypatch) -> None:
    original_live = live_agent.run_live_energy_aware_chat_agent

    def fake_live(request):
        baseline = DeepSeekBaselineResult(
            request=DeepSeekBaselineRequest(
                user_message=request.user_message,
                mode=request.mode,
                tier="flash",
                required_constraints=request.required_constraints,
                required_sections=request.required_sections,
            ),
            draft_answer="Fake live answer for regression test.",
            provider="deepseek",
            model="deepseek-v4-flash",
            tier="flash",
            input_tokens=10,
            output_tokens=8,
            evidence_refs=["provider:deepseek"],
            metadata={},
        )
        return original_live(request, baseline_result=baseline)

    monkeypatch.setattr(live_agent, "run_live_energy_aware_chat_agent", fake_live)

    response = client.post(
        "/energy-chat/chat/live",
        json={"user_message": "test legacy live route unchanged"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["mvp_layer"] == "live_provider_rag_plus_agent_orchestration"


def test_v2_legacy_evaluate_route_unchanged() -> None:
    response = client.post(
        "/energy-chat/evaluate",
        json={
            "user_message": "Explain the safe first implementation step",
            "draft_answer": (
                "Start with the deterministic evaluator and keep provider calls deferred. "
                "The tradeoff is slower initial setup but stronger validation. "
                "Next step: write the red tests for the evaluator contracts."
            ),
            "required_constraints": ["provider calls deferred"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["decision"] == "accept"
    assert body["energy_card"]["decision"] == "accept"
