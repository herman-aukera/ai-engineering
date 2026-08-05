from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_default_cors_allows_only_explicit_local_origins() -> None:
    allowed = client.options(
        "/eacode/status",
        headers={
            "Origin": "http://127.0.0.1:8000",
            "Access-Control-Request-Method": "GET",
        },
    )
    blocked = client.options(
        "/eacode/status",
        headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:8000"
    assert "access-control-allow-origin" not in blocked.headers
