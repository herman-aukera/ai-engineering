from __future__ import annotations

from pathlib import Path
from typing import Any

import energy_chat_streamlit_app as energy_ui

STREAMLIT_SOURCE = Path("energy_chat_streamlit_app.py").read_text(encoding="utf-8")


def test_energy_chat_streamlit_demo_points_to_evaluate_endpoint():
    assert 'ENERGY_CHAT_EVALUATE_PATH = "/energy-chat/evaluate"' in STREAMLIT_SOURCE
    assert "def build_energy_chat_evaluate_url" in STREAMLIT_SOURCE
    assert "def post_energy_chat_evaluation_request" in STREAMLIT_SOURCE


def test_energy_chat_streamlit_demo_points_to_benchmark_endpoint():
    assert (
        'ENERGY_CHAT_BENCHMARK_PATH = "/energy-chat/benchmark/deepseek-energy-aware"'
        in STREAMLIT_SOURCE
    )
    assert "def build_energy_chat_benchmark_url" in STREAMLIT_SOURCE
    assert "def post_energy_chat_benchmark_request" in STREAMLIT_SOURCE
    assert "Benchmark harness" in STREAMLIT_SOURCE


def test_energy_chat_streamlit_demo_exposes_visible_energy_card():
    assert "Energy Card" in STREAMLIT_SOURCE
    assert "Decision" in STREAMLIT_SOURCE
    assert "Energy" in STREAMLIT_SOURCE
    assert "Hard constraints passed" in STREAMLIT_SOURCE
    assert "Remaining caveats" in STREAMLIT_SOURCE


def test_energy_chat_streamlit_demo_exposes_measurement_only_benchmark_panel():
    assert "Measurement-only benchmark summary" in STREAMLIT_SOURCE
    assert "does not claim improvement" in STREAMLIT_SOURCE
    assert "Claim status" in STREAMLIT_SOURCE
    assert "Accepted after repair" in STREAMLIT_SOURCE


def test_energy_chat_streamlit_demo_reads_energy_card_api_contract():
    assert 'result.get("energy_card")' in STREAMLIT_SOURCE
    assert "render_energy_card(extract_energy_card(result))" in STREAMLIT_SOURCE


def test_extract_energy_card_prefers_api_contract_over_legacy_card():
    result = {
        "card": {"decision": "unknown", "energy": "unknown"},
        "energy_card": {
            "decision": "accept",
            "energy": 0,
            "hard_constraints_passed": True,
            "repairs": 0,
            "evidence": ["policy", "critic_results"],
            "remaining_caveats": [],
        },
    }

    assert energy_ui.extract_energy_card(result) == result["energy_card"]


def test_extract_energy_card_keeps_legacy_card_fallback():
    result = {
        "card": {
            "decision": "repair",
            "energy": 300,
            "hard_constraints_passed": False,
        }
    }

    assert energy_ui.extract_energy_card(result) == result["card"]


def test_extract_energy_card_handles_missing_or_invalid_card():
    assert energy_ui.extract_energy_card({}) == {}
    assert energy_ui.extract_energy_card({"energy_card": "not-a-dict"}) == {}


def test_extract_findings_reads_current_score_shape():
    result = {
        "findings": [{"legacy": True}],
        "score": {"findings": [{"violation_id": "missing_next_action"}]},
    }

    assert energy_ui.extract_findings(result) == [{"legacy": True}]
    assert energy_ui.extract_findings({"score": result["score"]}) == [
        {"violation_id": "missing_next_action"}
    ]


def test_build_energy_chat_payload_uses_chat_lite_by_default():
    payload = energy_ui.build_energy_chat_payload(
        user_message="Check whether this answer satisfies the constraints.",
        draft_answer="The next action is to run the validation gate before claiming success.",
    )

    assert payload == {
        "user_message": "Check whether this answer satisfies the constraints.",
        "draft_answer": "The next action is to run the validation gate before claiming success.",
        "mode": "chat_lite",
    }


def test_build_energy_chat_benchmark_payload_has_fixed_demo_cases():
    payload = energy_ui.build_energy_chat_benchmark_payload(run_id="demo-run")

    assert payload["run_id"] == "demo-run"
    assert payload["tier"] == "flash"
    assert [case["case_id"] for case in payload["cases"]] == [
        "scoped_release_answer",
        "scope_creep_answer",
    ]


def test_format_decision_label_covers_mvp_decisions():
    assert energy_ui.format_decision_label("accept") == "✅ accept"
    assert energy_ui.format_decision_label("repair") == "🛠️ repair"
    assert energy_ui.format_decision_label("reject") == "⛔ reject"
    assert energy_ui.format_decision_label("clarify") == "❓ clarify"


def test_post_energy_chat_evaluation_request_posts_json_payload(monkeypatch):
    captured: dict[str, Any] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            captured["raise_for_status_called"] = True

        def json(self) -> dict[str, Any]:
            return {"decision": "accept"}

    def fake_post(url: str, json: dict[str, Any], timeout: tuple[int, int]) -> FakeResponse:
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(energy_ui.requests, "post", fake_post)
    monkeypatch.setenv("ESTIMADOR_BACKEND_URL", "https://example.test/")

    payload = energy_ui.build_energy_chat_payload(
        user_message="Review this answer.",
        draft_answer="The next action is to run tests.",
    )

    result = energy_ui.post_energy_chat_evaluation_request(payload)

    assert result == {"decision": "accept"}
    assert captured == {
        "url": "https://example.test/energy-chat/evaluate",
        "json": payload,
        "timeout": (10, 120),
        "raise_for_status_called": True,
    }


def test_post_energy_chat_benchmark_request_posts_json_payload(monkeypatch):
    captured: dict[str, Any] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            captured["raise_for_status_called"] = True

        def json(self) -> dict[str, Any]:
            return {"run_id": "demo-run", "cases_total": 2}

    def fake_post(url: str, json: dict[str, Any], timeout: tuple[int, int]) -> FakeResponse:
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(energy_ui.requests, "post", fake_post)
    monkeypatch.setenv("ESTIMADOR_BACKEND_URL", "https://example.test/")

    payload = energy_ui.build_energy_chat_benchmark_payload(run_id="demo-run")
    result = energy_ui.post_energy_chat_benchmark_request(payload)

    assert result == {"run_id": "demo-run", "cases_total": 2}
    assert captured == {
        "url": "https://example.test/energy-chat/benchmark/deepseek-energy-aware",
        "json": payload,
        "timeout": (10, 120),
        "raise_for_status_called": True,
    }


def test_summarize_benchmark_result_returns_claim_status():
    summary = energy_ui.summarize_benchmark_result(
        {
            "run_id": "demo-run",
            "cases_total": 2,
            "accepted_baseline": 1,
            "accepted_after_repair": 2,
            "repairs_attempted": 1,
            "hard_rejects": 0,
            "metadata": {"claim_status": "measurement_only_no_quality_claim"},
        }
    )

    assert summary == {
        "run_id": "demo-run",
        "cases_total": 2,
        "accepted_baseline": 1,
        "accepted_after_repair": 2,
        "repairs_attempted": 1,
        "hard_rejects": 0,
        "claim_status": "measurement_only_no_quality_claim",
    }


def test_benchmark_case_rows_flatten_response_shape():
    rows = energy_ui.benchmark_case_rows(
        {
            "results": [
                {
                    "case": {"case_id": "case-001"},
                    "baseline_evaluation": {
                        "decision": {"decision": "repair"},
                        "score": {"total_energy": 700},
                    },
                    "final_decision": "accept",
                    "final_energy": 0,
                    "energy_delta_after_repair": -700,
                    "accepted_after_repair": True,
                }
            ]
        }
    )

    assert rows == [
        {
            "case_id": "case-001",
            "baseline_decision": "repair",
            "final_decision": "accept",
            "baseline_energy": 700,
            "final_energy": 0,
            "energy_delta_after_repair": -700,
            "accepted_after_repair": True,
        }
    ]
