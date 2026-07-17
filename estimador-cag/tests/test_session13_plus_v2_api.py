from __future__ import annotations

from fastapi.testclient import TestClient

from scripts.session13_plus_demo_api import app


def test_v2_api_runs_one_canonical_execution_through_both_gates() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/v2/estimations",
            json={
                "context": {
                    "transcript": "Build secure authentication with an auditable event trail."
                },
                "profile": "human_controlled",
            },
        )
        assert created.status_code == 200, created.text
        first = created.json()
        estimation_id = first["estimation"]["estimation_id"]
        assert first["estimation"]["stage"] == "structure"
        assert first["estimation"]["execution_policy"]["human_review_mode"] == "required"

        structure = client.post(
            f"/api/v2/estimations/{estimation_id}/actions",
            json={
                "gate": "structure",
                "action": "approve",
                "expected_revision": 0,
            },
        )
        assert structure.status_code == 200, structure.text
        second = structure.json()
        assert second["estimation"]["stage"] == "human_approval"
        task = second["estimation"]["modules"][0]["tasks"][0]
        assert task["estimate"]["hours_expected"] == 40.0
        assert task["estimate"]["cost_eur"] == 0.0

        final = client.post(
            f"/api/v2/estimations/{estimation_id}/actions",
            json={
                "gate": "final",
                "action": "approve",
                "expected_revision": 0,
                "actor": "v2-reviewer",
            },
        )
        assert final.status_code == 200, final.text
        assert final.json()["estimation"]["execution_status"] == "completed"

        inspected = client.get(f"/api/v2/estimations/{estimation_id}")
        assert inspected.status_code == 200
        assert inspected.json()["estimation"]["total_hours"] == 40.0

        history = client.get(f"/api/v2/estimations/{estimation_id}/checkpoints")
        assert history.status_code == 200
        assert len(history.json()["checkpoints"]) >= 3

        audit = client.get(f"/api/v2/estimations/{estimation_id}/audit")
        assert audit.status_code == 200
        assert "transcript" not in str(audit.json()).lower()


def test_v2_action_contract_rejects_wrong_gate_fields() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v2/estimations/00000000-0000-0000-0000-000000000001/actions",
            json={
                "gate": "final",
                "action": "approve",
                "expected_revision": 0,
            },
        )
    assert response.status_code == 422
