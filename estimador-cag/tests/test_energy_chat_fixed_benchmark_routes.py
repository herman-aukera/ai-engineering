from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_fixed_benchmark_result_route_returns_measurement_only_evidence() -> None:
    response = client.get("/energy-chat/benchmark/fixed")

    assert response.status_code == 200
    body = response.json()
    assert body["cases_total"] == 5
    assert body["accepted_baseline"] == 0
    assert body["accepted_after_repair"] == 4
    assert body["metadata"]["claim_status"] == "measurement_only_no_quality_claim"
    assert body["metadata"]["provider_calls"] == 0
    assert body["metadata"]["quality_claim_allowed"] is False


def test_fixed_benchmark_report_route_returns_markdown_boundary() -> None:
    response = client.get("/energy-chat/benchmark/fixed/report")

    assert response.status_code == 200
    assert "# Energy Aware Chat Fixed Benchmark Report" in response.text
    assert "measurement_only_no_quality_claim" in response.text
    assert "does not prove live provider quality improvement" in response.text
