"""Security contracts for public EACHAT V2 routes and browser delivery."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_v2_browser_response_sets_required_security_headers(monkeypatch) -> None:
    monkeypatch.setenv("EACHAT_V2_ENABLED", "true")
    response = client.get("/energy-chat/v2/demo")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )
    content_security_policy = response.headers["content-security-policy"]
    assert "default-src 'self'" in content_security_policy
    assert "frame-ancestors 'none'" in content_security_policy
    assert "connect-src 'self'" in content_security_policy
    assert response.headers["cache-control"] == "no-store"


def test_v2_api_response_does_not_expose_credentials_or_environment_values() -> None:
    response = client.post(
        "/energy-chat/v2/chat",
        json={"user_message": "Explain the Energy-Aware decision path."},
    )

    assert response.status_code == 200
    serialized = json.dumps(response.json(), sort_keys=True)
    forbidden = (
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "KIMI_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "postgresql://",
        "redis://",
        "BEGIN PRIVATE KEY",
    )
    assert all(value not in serialized for value in forbidden)


def test_openapi_does_not_embed_secret_or_database_values() -> None:
    serialized = json.dumps(client.get("/openapi.json").json(), sort_keys=True)

    assert "postgresql://" not in serialized
    assert "redis://" not in serialized
    assert "DEEPSEEK_API_KEY" not in serialized
    assert "OPENAI_API_KEY" not in serialized
    assert "KIMI_API_KEY" not in serialized


def test_cors_never_allows_credentials_for_arbitrary_origins() -> None:
    response = client.options(
        "/energy-chat/v2/chat",
        headers={
            "Origin": "https://attacker.invalid",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "*"
    assert "access-control-allow-credentials" not in response.headers


def test_v2_errors_are_sanitized_and_receive_security_headers() -> None:
    response = client.post(
        "/energy-chat/v2/chat",
        json={
            "user_message": "test",
            "context_profile": "max",
        },
    )

    assert response.status_code == 400
    serialized = json.dumps(response.json(), sort_keys=True)
    assert "Traceback" not in serialized
    assert "/home/runner/" not in serialized
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
