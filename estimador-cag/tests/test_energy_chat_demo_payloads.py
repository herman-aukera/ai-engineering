import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.energy_chat.contracts import (
    DeepSeekBenchmarkRequest,
    EnergyChatRequest,
    EvidenceBundleRequest,
    SourceNeedRequest,
)
from app.main import app

PAYLOAD_DIR = Path(__file__).resolve().parents[1] / "demo_payloads" / "energy_chat"
client = TestClient(app)


def _load_payload(name: str) -> dict:
    path = PAYLOAD_DIR / name
    assert path.exists(), f"Missing demo payload: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_demo_payload_directory_contains_expected_contract_examples() -> None:
    assert sorted(path.name for path in PAYLOAD_DIR.glob("*.json")) == [
        "benchmark_measurement.json",
        "evaluate_accept.json",
        "evaluate_repair_once.json",
        "evidence_bundle_project.json",
        "source_needed_project.json",
    ]


def test_evaluate_accept_payload_matches_contract_and_route() -> None:
    payload = _load_payload("evaluate_accept.json")
    request = EnergyChatRequest.model_validate(payload)

    response = client.post("/energy-chat/evaluate", json=request.model_dump())

    assert response.status_code == 200
    body = response.json()
    assert body["request"]["metadata"]["demo_case"] == "evaluate_accept"
    assert body["decision"]["decision"] == "accept"
    assert body["energy_card"]["decision"] == "accept"
    assert body["energy_card"]["hard_constraints_passed"] is True


def test_repair_once_payload_matches_contract_and_route() -> None:
    payload = _load_payload("evaluate_repair_once.json")
    request = EnergyChatRequest.model_validate(payload)

    response = client.post("/energy-chat/evaluate/repair-once", json=request.model_dump())

    assert response.status_code == 200
    body = response.json()
    assert body["initial_result"]["decision"]["decision"] == "repair"
    assert body["repair_attempted"] is True
    assert body["final_result"]["decision"]["decision"] == "accept"
    assert body["repaired_request"]["metadata"]["demo_case"] == "evaluate_repair_once"


def test_source_needed_project_payload_matches_contract_and_route() -> None:
    payload = _load_payload("source_needed_project.json")
    request = SourceNeedRequest.model_validate(payload)

    response = client.post("/energy-chat/source-needed", json=request.model_dump())

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "sources_required"
    assert body["requires_project_sources"] is True
    assert body["missing_evidence"] is True


def test_evidence_bundle_payload_matches_contract_and_route() -> None:
    payload = _load_payload("evidence_bundle_project.json")
    request = EvidenceBundleRequest.model_validate(payload)

    response = client.post("/energy-chat/evidence/bundle", json=request.model_dump())

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "project"
    assert body["trusted_refs"] == [
        "file:docs/energy_aware_chat_demo.md",
        "git:status-clean",
        "test:pytest-passed",
    ]
    assert body["can_support_project_claim"] is True


def test_benchmark_payload_matches_measurement_request_contract() -> None:
    payload = _load_payload("benchmark_measurement.json")
    request = DeepSeekBenchmarkRequest.model_validate(payload)

    assert request.run_id == "demo-measurement-only-001"
    assert request.tier == "flash"
    assert len(request.cases) == 1
    assert request.cases[0].metadata["demo_case"] == "scoped_answer"
