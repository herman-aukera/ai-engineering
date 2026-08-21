from __future__ import annotations

import pytest

from app.energy_aware_observability import EVENT_SCHEMA_VERSION, PROTOCOL_VERSION, OperationalEvent, safe_request_id


def test_operational_event_is_stable_sanitized_and_protocol_versioned() -> None:
    event = OperationalEvent(
        product="eachat", event_type="http_request", outcome="success",
        reason_code="request_completed", request_id="request-123", duration_ms=7,
        attributes={"method": "GET", "path": "/health", "status_code": "200"},
    ).as_dict()
    assert event["event_schema_version"] == EVENT_SCHEMA_VERSION == "energy-aware.event.v1"
    assert event["protocol_version"] == PROTOCOL_VERSION == "energy-aware.protocol.v1"
    assert event["reason_code"] == "request_completed"
    assert "authorization" not in event["attributes"]


def test_observability_rejects_sensitive_attribute_names_and_invalid_reason_codes() -> None:
    with pytest.raises(ValueError, match="sensitive"):
        OperationalEvent(
            product="eachat", event_type="http_request", outcome="error",
            reason_code="request_http_error", request_id="request-123", duration_ms=1,
            attributes={"authorization": "Bearer forbidden"},
        )
    with pytest.raises(ValueError, match="reason_code"):
        OperationalEvent(
            product="eachat", event_type="http_request", outcome="error",
            reason_code="Bad Reason", request_id="request-123", duration_ms=1,
        )


def test_request_id_accepts_safe_correlation_or_generates_server_id() -> None:
    assert safe_request_id("client.correlation-17") == "client.correlation-17"
    generated = safe_request_id("unsafe request id with spaces")
    assert generated.startswith("request-")
