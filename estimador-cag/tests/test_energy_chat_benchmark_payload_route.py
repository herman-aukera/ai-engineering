import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.energy_chat import benchmark
from app.energy_chat.contracts import DeepSeekBenchmarkRequest, DeepSeekBenchmarkRunResult
from app.main import app

PAYLOAD = Path("demo_payloads/energy_chat/benchmark_measurement.json")
client = TestClient(app)


def test_benchmark_demo_payload_posts_to_route_with_fake_runner(monkeypatch) -> None:
    payload = json.loads(PAYLOAD.read_text(encoding="utf-8"))

    def fake_run(request: DeepSeekBenchmarkRequest) -> DeepSeekBenchmarkRunResult:
        return DeepSeekBenchmarkRunResult(
            run_id=request.run_id or "fake-run",
            provider="deepseek",
            model="deepseek-v4-flash",
            tier=request.tier,
            cases_total=len(request.cases),
            accepted_baseline=0,
            accepted_after_repair=0,
            repairs_attempted=0,
            hard_rejects=0,
            results=[],
            metadata={"claim_status": "measurement_only_no_quality_claim"},
        )

    monkeypatch.setattr(benchmark, "run_deepseek_energy_benchmark", fake_run)

    response = client.post("/energy-chat/benchmark/deepseek-energy-aware", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == payload["run_id"]
    assert body["cases_total"] == len(payload["cases"])
    assert body["metadata"]["claim_status"] == "measurement_only_no_quality_claim"
