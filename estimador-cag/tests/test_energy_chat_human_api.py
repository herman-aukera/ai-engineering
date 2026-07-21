"""Production HTTP tests for typed human interrupt and resume."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.energy_chat.runtime_container import EnergyChatApplicationRuntime
from app.main import app

client = TestClient(app)


def _install_runtime() -> object:
    previous = app.state.energy_chat_runtime
    app.state.energy_chat_runtime = EnergyChatApplicationRuntime()
    return previous


def _start_escalation(thread_id: str) -> dict:
    response = client.post(
        "/energy-chat/v2/chat/human",
        json={
            "user_message": "Approve the production release.",
            "thread_id": thread_id,
            "request_id": f"request-{thread_id}",
            "trace_id": f"trace-{thread_id}",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _resume_payload(pending_action: dict, **overrides) -> dict:
    payload = {
        "action_id": pending_action["action_id"],
        "action": pending_action["action"],
        "expected_revision": pending_action["expected_revision"],
        "actor": "reviewer-test",
        "payload": {"response": "approved for deterministic test"},
    }
    payload.update(overrides)
    return payload


def test_escalation_interrupt_and_successful_resume_use_one_provider_call() -> None:
    previous = _install_runtime()
    try:
        started = _start_escalation("thread-human-success")
        action = started["human_action_request"]

        assert started["graph_status"] == "awaiting_human"
        assert started["final_disposition"] == "escalate"
        assert action["action"] == "escalate_response"
        assert action["expected_revision"] == 1
        assert started["provider_metrics_summary"]["provider_call_count"] == 1
        assert started["ledger_entry_ids"] == []

        pending_state = client.get(
            "/energy-chat/v2/threads/thread-human-success/state"
        )
        assert pending_state.status_code == 200
        assert pending_state.json()["human_action_pending"] is True
        assert pending_state.json()["human_action_request"] == action

        resumed = client.post(
            "/energy-chat/v2/threads/thread-human-success/resume",
            json=_resume_payload(action),
        )
        assert resumed.status_code == 200, resumed.text
        body = resumed.json()
        assert body["graph_status"] == "completed"
        assert body["final_disposition"] == "escalate"
        assert body["human_action_request"] is None
        assert body["provider_metrics_summary"]["provider_call_count"] == 1
        assert len(body["ledger_entry_ids"]) == 1

        completed_state = client.get(
            "/energy-chat/v2/threads/thread-human-success/state"
        )
        assert completed_state.status_code == 200
        assert completed_state.json()["human_action_pending"] is False
        assert completed_state.json()["graph_status"] == "completed"
    finally:
        app.state.energy_chat_runtime = previous


def test_vague_request_produces_clarification_interrupt() -> None:
    previous = _install_runtime()
    try:
        response = client.post(
            "/energy-chat/v2/chat/human",
            json={
                "user_message": "help",
                "thread_id": "thread-human-clarify",
            },
        )
    finally:
        app.state.energy_chat_runtime = previous

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["graph_status"] == "awaiting_human"
    assert body["final_disposition"] == "clarify"
    assert body["human_action_request"]["action"] == "clarify_response"


def test_stale_revision_is_rejected_by_production_resume_path() -> None:
    previous = _install_runtime()
    try:
        started = _start_escalation("thread-human-stale")
        action = started["human_action_request"]
        response = client.post(
            "/energy-chat/v2/threads/thread-human-stale/resume",
            json=_resume_payload(
                action,
                expected_revision=action["expected_revision"] + 1,
            ),
        )
    finally:
        app.state.energy_chat_runtime = previous

    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "stale_human_action"


def test_wrong_action_id_and_type_are_rejected() -> None:
    previous = _install_runtime()
    try:
        started = _start_escalation("thread-human-mismatch")
        action = started["human_action_request"]
        wrong_id = client.post(
            "/energy-chat/v2/threads/thread-human-mismatch/resume",
            json=_resume_payload(action, action_id="wrong-action-id"),
        )
        wrong_type = client.post(
            "/energy-chat/v2/threads/thread-human-mismatch/resume",
            json=_resume_payload(action, action="clarify_response"),
        )
    finally:
        app.state.energy_chat_runtime = previous

    assert wrong_id.status_code == 409
    assert wrong_id.json()["detail"]["error"] == "human_action_mismatch"
    assert wrong_type.status_code == 409
    assert wrong_type.json()["detail"]["error"] == "human_action_mismatch"


def test_wrong_thread_and_duplicate_resume_fail_closed() -> None:
    previous = _install_runtime()
    try:
        started = _start_escalation("thread-human-duplicate")
        action = started["human_action_request"]
        missing = client.post(
            "/energy-chat/v2/threads/thread-human-missing/resume",
            json=_resume_payload(action),
        )
        first = client.post(
            "/energy-chat/v2/threads/thread-human-duplicate/resume",
            json=_resume_payload(action),
        )
        duplicate = client.post(
            "/energy-chat/v2/threads/thread-human-duplicate/resume",
            json=_resume_payload(action),
        )
    finally:
        app.state.energy_chat_runtime = previous

    assert missing.status_code == 404
    assert missing.json()["detail"]["error"] == "thread_checkpoint_not_found"
    assert first.status_code == 200
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["error"] == "human_action_already_resumed"


def test_human_route_rejects_live_profile_and_fallback() -> None:
    previous = _install_runtime()
    try:
        live = client.post(
            "/energy-chat/v2/chat/human",
            json={
                "user_message": "Approve the production release.",
                "execution_profile": "live_bounded",
            },
        )
        fallback = client.post(
            "/energy-chat/v2/chat/human",
            json={
                "user_message": "Approve the production release.",
                "allow_provider_fallback": True,
                "fallback_provider_allowlist": ["deepseek"],
            },
        )
    finally:
        app.state.energy_chat_runtime = previous

    assert live.status_code == 400
    assert live.json()["detail"]["error"] == "unsupported_execution_profile"
    assert fallback.status_code == 400
    assert fallback.json()["detail"]["error"] == "unsupported_allow_provider_fallback"
