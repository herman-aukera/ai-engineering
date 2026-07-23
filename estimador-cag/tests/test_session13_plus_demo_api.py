from fastapi.testclient import TestClient

from scripts.session13_plus_demo_api import app


def test_demo_api_exercises_both_gates_history_and_audit() -> None:
    with TestClient(app) as client:
        started = client.post(
            "/api/v1/estimate/graph/reviewed/start",
            json={
                "transcript": "Build secure authentication with an audit trail.",
                "human_review_mode": "required",
            },
        )
        assert started.status_code == 200
        first = started.json()
        estimation_id = first["estimation_id"]
        assert first["interrupts"][0]["value"]["gate"] == "structure_review"

        structure = client.post(
            f"/api/v1/estimate/graph/reviewed/{estimation_id}/resume",
            json={"action": "approve", "expected_revision": 0},
        )
        assert structure.status_code == 200
        second = structure.json()
        assert second["interrupts"][0]["value"]["gate"] == "final_estimate_review"
        assert second["state"]["estimate"]["total_hours"] == 40.0

        final = client.post(
            f"/api/v1/estimate/graph/reviewed/{estimation_id}/resume/final",
            json={
                "action": "approve",
                "expected_revision": 0,
                "actor": "demo-reviewer",
            },
        )
        assert final.status_code == 200
        assert final.json()["execution_status"] == "completed"

        history = client.get(
            f"/api/v1/estimate/graph/reviewed/{estimation_id}/checkpoints"
        )
        assert history.status_code == 200
        assert len(history.json()["checkpoints"]) >= 3

        audit = client.get(f"/api/v1/estimate/graph/reviewed/{estimation_id}/audit")
        assert audit.status_code == 200
        packet = audit.json()["packet"]
        assert packet["final_estimate"]["total_hours"] == 40.0
        assert packet["human_decisions"]
