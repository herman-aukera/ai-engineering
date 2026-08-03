from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_beta_demo_exposes_inspectable_authority_timeline() -> None:
    response = client.post(
        "/eacode/demo",
        json={
            "proposal_id": "api-demo-1",
            "objective": "Add a safe health check.",
            "spec_id": "0011-demo-ready-beta",
            "patch": "def health():\n    return 'todo'\n",
            "changed_files": ["app/health.py"],
            "proposed_commands": [["pytest", "-q", "tests/test_health.py"]],
            "human_authorization": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["initial_decision"]["disposition"] == "repair"
    assert payload["final_decision"]["disposition"] == "accept"
    assert payload["authorization"]["authorized"] is True
    assert payload["execution"]["execution_performed"] is True
    assert payload["rollback"]["available"] is True

    inspection = client.get("/eacode/demo/api-demo-1")
    assert inspection.status_code == 200
    assert inspection.json()["proposal"]["proposal_id"] == "api-demo-1"


def test_missing_demo_run_returns_404() -> None:
    assert client.get("/eacode/demo/unknown").status_code == 404


def test_ui_exposes_beta_journey_separately_from_provider_selector() -> None:
    response = client.get("/eacode/ui")
    assert response.status_code == 200
    assert 'id="beta-demo"' in response.text
    assert "Run deterministic beta demo" in response.text
    assert "Repair and authority timeline" in response.text
