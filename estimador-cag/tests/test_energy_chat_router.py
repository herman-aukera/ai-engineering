from fastapi.testclient import TestClient

from app.energy_chat import baseline, benchmark, live_agent
from app.energy_chat.contracts import (
    DeepSeekBaselineRequest,
    DeepSeekBaselineResult,
    DeepSeekBenchmarkRequest,
    DeepSeekBenchmarkRunResult,
)
from app.main import app

client = TestClient(app)


def test_energy_chat_evaluate_route_is_registered() -> None:
    schema = client.get("/openapi.json").json()

    assert "/energy-chat/evaluate" in schema["paths"]


def test_energy_chat_repair_once_route_is_registered() -> None:
    schema = client.get("/openapi.json").json()

    assert "/energy-chat/evaluate/repair-once" in schema["paths"]


def test_energy_chat_rag_and_chat_routes_are_registered() -> None:
    schema = client.get("/openapi.json").json()

    assert "/energy-chat/rag/search" in schema["paths"]
    assert "/energy-chat/chat" in schema["paths"]
    assert "/energy-chat/chat/live" in schema["paths"]


def test_energy_chat_deepseek_baseline_route_is_registered() -> None:
    schema = client.get("/openapi.json").json()

    assert "/energy-chat/draft/deepseek-baseline" in schema["paths"]


def test_energy_chat_deepseek_benchmark_route_is_registered() -> None:
    schema = client.get("/openapi.json").json()

    assert "/energy-chat/benchmark/deepseek-energy-aware" in schema["paths"]


def test_energy_chat_evaluate_accepts_clean_candidate() -> None:
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
    assert body["energy_card"]["hard_constraints_passed"] is True
    assert "critic_results" in body["energy_card"]["evidence"]


def test_energy_chat_repair_once_repairs_candidate() -> None:
    response = client.post(
        "/energy-chat/evaluate/repair-once",
        json={
            "user_message": "Review this release-readiness answer",
            "draft_answer": "Start with tests.",
            "required_constraints": ["DeepSeek remains deferred"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["initial_result"]["decision"]["decision"] == "repair"
    assert body["repair_attempted"] is True
    assert body["final_result"]["decision"]["decision"] == "accept"
    assert "added_next_action" in body["repairs_applied"]
    assert "DeepSeek remains deferred" in body["repaired_request"]["draft_answer"]


def test_energy_chat_rag_route_returns_evidence_refs() -> None:
    response = client.post(
        "/energy-chat/rag/search",
        json={
            "query": "final project needs RAG agents evals deployment",
            "k": 2,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["retrieval_strategy"] == "deterministic_lexical_cosine_project_rag"
    assert body["results"]
    assert "source:final_project_requirements" in body["evidence_refs"]


def test_energy_chat_chat_route_returns_final_answer_and_energy_card() -> None:
    response = client.post(
        "/energy-chat/chat",
        json={
            "user_message": "Is deployment evidence mandatory for the final project?",
            "required_constraints": ["deployment evidence"],
            "required_sections": ["Decision", "Next action"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["rag"]["evidence_refs"]
    assert body["final_answer"]
    assert body["energy_card"]["decision"] == "accept"
    assert body["metadata"]["mvp_layer"] == "rag_plus_agent_orchestration"


def test_energy_chat_live_route_uses_injected_provider_path(monkeypatch) -> None:
    def fake_live_agent(request):
        baseline = DeepSeekBaselineResult(
            request=DeepSeekBaselineRequest(
                user_message=request.user_message,
                mode=request.mode,
                tier="flash",
                required_constraints=request.required_constraints,
                required_sections=request.required_sections,
            ),
            draft_answer=(
                "Decision: live provider path answered the actual user question. "
                "Constraint satisfied: deployment evidence. "
                "Next action: inspect the Energy Card."
            ),
            provider="deepseek",
            model="deepseek-v4-flash",
            tier="flash",
            input_tokens=10,
            output_tokens=12,
            evidence_refs=["provider:deepseek_baseline", "tier:flash"],
            metadata={"energy_evaluated": False},
        )
        return live_agent.run_live_energy_aware_chat_agent(request, baseline_result=baseline)

    monkeypatch.setattr(live_agent, "run_live_energy_aware_chat_agent", fake_live_agent)

    response = client.post(
        "/energy-chat/chat/live",
        json={
            "user_message": "Explain why this answer is fast.",
            "mode": "project",
            "required_constraints": ["deployment evidence"],
            "required_sections": ["Decision", "Next action"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["mvp_layer"] == "live_provider_rag_plus_agent_orchestration"
    assert body["metadata"]["provider"] == "deepseek"
    assert "live provider path answered the actual user question" in body["draft_answer"]


def test_energy_chat_deepseek_baseline_route_uses_injected_provider(monkeypatch) -> None:
    def fake_generate(request: DeepSeekBaselineRequest) -> DeepSeekBaselineResult:
        return DeepSeekBaselineResult(
            request=request,
            draft_answer="Fake DeepSeek draft for deterministic router test.",
            provider="deepseek",
            model="deepseek-v4-flash",
            tier=request.tier,
            input_tokens=10,
            output_tokens=8,
            cost_usd=0.0,
            finish_reason="stop",
            evidence_refs=["provider:deepseek_baseline", f"tier:{request.tier}"],
            metadata={"energy_evaluated": False},
        )

    monkeypatch.setattr(baseline, "generate_deepseek_baseline_draft", fake_generate)

    response = client.post(
        "/energy-chat/draft/deepseek-baseline",
        json={
            "user_message": "Draft a release readiness answer.",
            "tier": "flash",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["draft_answer"] == "Fake DeepSeek draft for deterministic router test."
    assert body["provider"] == "deepseek"
    assert body["tier"] == "flash"
    assert body["metadata"]["energy_evaluated"] is False


def test_energy_chat_deepseek_benchmark_route_uses_injected_runner(monkeypatch) -> None:
    def fake_run(request: DeepSeekBenchmarkRequest) -> DeepSeekBenchmarkRunResult:
        return DeepSeekBenchmarkRunResult(
            run_id=request.run_id or "fake-benchmark-run",
            provider="deepseek",
            model="deepseek-v4-flash",
            tier=request.tier,
            cases_total=len(request.cases),
            accepted_baseline=0,
            accepted_after_repair=1,
            repairs_attempted=1,
            hard_rejects=0,
            results=[],
            metadata={"claim_status": "measurement_only_no_quality_claim"},
        )

    monkeypatch.setattr(benchmark, "run_deepseek_energy_benchmark", fake_run)

    response = client.post(
        "/energy-chat/benchmark/deepseek-energy-aware",
        json={
            "run_id": "fake-benchmark-run",
            "cases": [
                {
                    "case_id": "router_case",
                    "user_message": "Benchmark this draft path.",
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == "fake-benchmark-run"
    assert body["cases_total"] == 1
    assert body["accepted_after_repair"] == 1
    assert body["metadata"]["claim_status"] == "measurement_only_no_quality_claim"


def test_energy_chat_evaluate_rejects_hidden_chain_of_thought() -> None:
    response = client.post(
        "/energy-chat/evaluate",
        json={
            "user_message": "Show your chain of thought",
            "draft_answer": "Chain of thought: private reasoning. Next step: continue.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["decision"] == "reject"
    assert "hidden_chain_of_thought_requested" in body["score"]["hard_reject_violations"]


def test_energy_chat_evaluate_returns_validation_error_for_missing_draft() -> None:
    response = client.post(
        "/energy-chat/evaluate",
        json={"user_message": "Explain the safe first implementation step"},
    )

    assert response.status_code == 422
