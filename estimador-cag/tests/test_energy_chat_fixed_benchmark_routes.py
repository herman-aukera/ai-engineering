from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_fixed_benchmark_result_route_returns_bounded_quality_evidence() -> None:
    response = client.get("/energy-chat/benchmark/fixed")

    assert response.status_code == 200
    body = response.json()
    assert body["cases_total"] == 5
    assert body["accepted_baseline"] == 0
    assert body["accepted_after_repair"] == 4
    assert body["metadata"]["claim_status"] == (
        "deterministic_fixed_corpus_energy_reduction"
    )
    assert body["metadata"]["claim_scope"] == "committed deterministic corpus only"
    assert body["metadata"]["provider_calls"] == 0
    assert body["metadata"]["quality_claim_allowed"] is True
    assert body["metadata"]["live_provider_quality_proven"] is False
    assert body["average_energy_delta_after_repair"] < 0
    assert body["accepted_hard_reject_exposures"] == 0


def test_fixed_benchmark_report_route_preserves_external_claim_boundary() -> None:
    response = client.get("/energy-chat/benchmark/fixed/report")

    assert response.status_code == 200
    assert "# Energy Aware Chat Fixed Benchmark Report" in response.text
    assert "deterministic_fixed_corpus_energy_reduction" in response.text
    assert "committed deterministic corpus only" in response.text
    assert "does not prove live provider quality improvement" in response.text
    assert "superiority over DeepSeek, Kimi, OpenAI" in response.text
