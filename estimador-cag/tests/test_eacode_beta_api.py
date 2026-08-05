from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app
from energy_core.identity import SessionSigner

client = TestClient(app)
SIGNING_KEY = "test-eacode-signing-key-32-bytes-minimum"


def _payload(proposal_id: str) -> dict[str, object]:
    return {
        "proposal_id": proposal_id,
        "objective": "Add a safe health check.",
        "spec_id": "0012-production-hardening",
        "patch": "def health():\n    return 'todo'\n",
        "changed_files": ["app/health.py"],
        "proposed_commands": [["pytest", "-q", "tests/test_health.py"]],
    }


def _token(*roles: str, user_id: str = "operator-1") -> str:
    return SessionSigner(SIGNING_KEY.encode()).issue(
        user_id=user_id,
        roles=roles,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )


def _headers(*roles: str, user_id: str = "operator-1") -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(*roles, user_id=user_id)}"}


def test_beta_demo_requires_server_session_and_persists_completed_timeline(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("EACODE_DEMO_DB_PATH", str(tmp_path / "eacode.sqlite3"))
    monkeypatch.setenv("EACODE_SESSION_SIGNING_KEY", SIGNING_KEY)
    headers = _headers("operator")

    assert client.post("/eacode/demo", json=_payload("unsigned")).status_code == 401
    prepared_response = client.post(
        "/eacode/demo",
        headers=headers,
        json=_payload("api-demo-1"),
    )
    assert prepared_response.status_code == 201
    prepared = prepared_response.json()
    assert prepared["initial_decision"]["disposition"] == "repair"
    assert prepared["final_decision"]["disposition"] == "escalate"
    assert prepared["authorization"]["authorized"] is False
    assert prepared["execution"]["execution_performed"] is False
    assert prepared["effective_proposal"]["patch"].endswith("return 'ok'\n")

    assert client.post("/eacode/demo/api-demo-1/authorize").status_code == 401
    authorization_response = client.post(
        "/eacode/demo/api-demo-1/authorize",
        headers=headers,
    )
    assert authorization_response.status_code == 201
    receipt_id = authorization_response.json()["receipt_id"]

    execution_response = client.post(
        "/eacode/demo/api-demo-1/execute",
        headers=headers,
        json={"receipt_id": receipt_id},
    )
    assert execution_response.status_code == 200
    completed = execution_response.json()
    assert completed["final_decision"]["disposition"] == "accept"
    assert completed["authorization"]["authorized"] is True
    assert completed["authorization"]["source"] == "server_session_receipt"
    assert completed["execution"]["execution_performed"] is True

    inspection = client.get("/eacode/demo/api-demo-1", headers=headers)
    assert inspection.status_code == 200
    assert inspection.json()["timeline"][-1]["event_type"] == "reevaluation"

    replay = client.post(
        "/eacode/demo/api-demo-1/execute",
        headers=headers,
        json={"receipt_id": receipt_id},
    )
    assert replay.status_code == 409


def test_viewer_can_prepare_and_inspect_but_cannot_authorize(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("EACODE_DEMO_DB_PATH", str(tmp_path / "eacode.sqlite3"))
    monkeypatch.setenv("EACODE_SESSION_SIGNING_KEY", SIGNING_KEY)
    viewer = _headers("viewer", user_id="viewer-1")

    assert (
        client.post("/eacode/demo", headers=viewer, json=_payload("api-demo-2")).status_code
        == 201
    )
    assert client.get("/eacode/demo/api-demo-2", headers=viewer).status_code == 200
    assert (
        client.post("/eacode/demo/api-demo-2/authorize", headers=viewer).status_code
        == 403
    )


def test_other_tenant_cannot_read_or_authorize_proposal(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("EACODE_DEMO_DB_PATH", str(tmp_path / "eacode.sqlite3"))
    monkeypatch.setenv("EACODE_SESSION_SIGNING_KEY", SIGNING_KEY)
    owner = _headers("operator", user_id="owner-1")
    other = _headers("operator", user_id="owner-2")

    assert (
        client.post("/eacode/demo", headers=owner, json=_payload("tenant-demo")).status_code
        == 201
    )
    assert client.get("/eacode/demo/tenant-demo", headers=other).status_code == 404
    assert (
        client.post("/eacode/demo/tenant-demo/authorize", headers=other).status_code
        == 404
    )
    assert client.get(
        "/eacode/demo/tenant-demo",
        headers=_headers("admin", user_id="admin-1"),
    ).status_code == 200


def test_client_controlled_human_authorization_is_rejected(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("EACODE_DEMO_DB_PATH", str(tmp_path / "eacode.sqlite3"))
    monkeypatch.setenv("EACODE_SESSION_SIGNING_KEY", SIGNING_KEY)
    payload = _payload("api-demo-3")
    payload["human_authorization"] = True

    response = client.post(
        "/eacode/demo",
        headers=_headers("operator"),
        json=payload,
    )

    assert response.status_code == 422


def test_missing_demo_run_returns_404_for_signed_session(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("EACODE_DEMO_DB_PATH", str(tmp_path / "eacode.sqlite3"))
    monkeypatch.setenv("EACODE_SESSION_SIGNING_KEY", SIGNING_KEY)
    assert (
        client.get("/eacode/demo/unknown", headers=_headers("viewer")).status_code
        == 404
    )


def test_ui_exposes_server_owned_authorization_boundary() -> None:
    response = client.get("/eacode/ui")
    assert response.status_code == 200
    assert 'id="beta-demo"' in response.text
    assert 'id="operator-token"' in response.text
    assert "one-time server-issued receipt" in response.text
    assert "Repair and authority timeline" in response.text
