"""Application-lifetime checkpoint and HTTP replay proof for EACHAT V2."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.energy_chat import runtime_container
from app.energy_chat.runtime_container import EnergyChatApplicationRuntime
from app.main import app

client = TestClient(app)


def _replace_runtime() -> tuple[object, EnergyChatApplicationRuntime]:
    previous = app.state.energy_chat_runtime
    current = EnergyChatApplicationRuntime()
    app.state.energy_chat_runtime = current
    return previous, current


def test_separate_http_replay_reads_checkpoint_without_second_graph_call(
    monkeypatch,
) -> None:
    previous, _ = _replace_runtime()
    original = runtime_container.run_graph_chat_v2
    calls = 0

    def counting_run(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(runtime_container, "run_graph_chat_v2", counting_run)
    try:
        first = client.post(
            "/energy-chat/v2/chat",
            json={
                "user_message": "Explain the graph backbone architecture.",
                "thread_id": "thread-http-replay",
                "request_id": "request-http-replay",
                "trace_id": "trace-http-replay",
            },
        )
        replay = client.post(
            "/energy-chat/v2/threads/thread-http-replay/replay"
        )
    finally:
        app.state.energy_chat_runtime = previous

    assert first.status_code == 200
    assert replay.status_code == 200
    assert calls == 1
    first_body = first.json()
    replay_body = replay.json()
    assert first_body["checkpoint_id"]
    assert replay_body["checkpoint_id"] == first_body["checkpoint_id"]
    assert replay_body["replayed_from_checkpoint"] is True
    assert replay_body["final_answer"] == first_body["final_answer"]
    assert replay_body["provider_metrics_summary"] == first_body[
        "provider_metrics_summary"
    ]


def test_thread_state_endpoint_projects_safe_checkpoint_metadata() -> None:
    previous, _ = _replace_runtime()
    try:
        created = client.post(
            "/energy-chat/v2/chat",
            json={
                "user_message": "Explain the Decision Ledger.",
                "thread_id": "thread-state-proof",
                "request_id": "request-state-proof",
                "trace_id": "trace-state-proof",
            },
        )
        state = client.get(
            "/energy-chat/v2/threads/thread-state-proof/state"
        )
    finally:
        app.state.energy_chat_runtime = previous

    assert created.status_code == 200
    assert state.status_code == 200
    body = state.json()
    assert body["thread_id"] == "thread-state-proof"
    assert body["request_id"] == "request-state-proof"
    assert body["checkpoint_id"] == created.json()["checkpoint_id"]
    assert body["provider_call_count"] == 1
    assert body["candidate_count"] >= 1
    assert body["process_local"] is True
    assert body["restart_persistent"] is False


def test_application_runtime_keeps_threads_isolated() -> None:
    previous, _ = _replace_runtime()
    try:
        first = client.post(
            "/energy-chat/v2/chat",
            json={
                "user_message": "Explain evidence routing.",
                "thread_id": "thread-isolated-a",
                "request_id": "request-isolated-a",
                "trace_id": "trace-isolated-a",
            },
        )
        second = client.post(
            "/energy-chat/v2/chat",
            json={
                "user_message": "Explain bounded repair.",
                "thread_id": "thread-isolated-b",
                "request_id": "request-isolated-b",
                "trace_id": "trace-isolated-b",
            },
        )
        first_state = client.get(
            "/energy-chat/v2/threads/thread-isolated-a/state"
        )
        second_state = client.get(
            "/energy-chat/v2/threads/thread-isolated-b/state"
        )
    finally:
        app.state.energy_chat_runtime = previous

    assert first.status_code == 200
    assert second.status_code == 200
    assert first_state.status_code == 200
    assert second_state.status_code == 200
    assert first_state.json()["request_id"] == "request-isolated-a"
    assert second_state.json()["request_id"] == "request-isolated-b"
    assert first_state.json()["checkpoint_id"] != second_state.json()["checkpoint_id"]


def test_same_thread_with_different_request_fails_closed() -> None:
    previous, _ = _replace_runtime()
    try:
        first = client.post(
            "/energy-chat/v2/chat",
            json={
                "user_message": "Explain graph state.",
                "thread_id": "thread-conflict-proof",
            },
        )
        conflict = client.post(
            "/energy-chat/v2/chat",
            json={
                "user_message": "A different request on the completed thread.",
                "thread_id": "thread-conflict-proof",
            },
        )
    finally:
        app.state.energy_chat_runtime = previous

    assert first.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["error"] == "thread_checkpoint_conflict"


def test_missing_thread_and_process_restart_report_no_checkpoint() -> None:
    previous, _ = _replace_runtime()
    try:
        missing = client.post(
            "/energy-chat/v2/threads/thread-does-not-exist/replay"
        )
        created = client.post(
            "/energy-chat/v2/chat",
            json={
                "user_message": "Explain process-local replay.",
                "thread_id": "thread-restart-proof",
            },
        )
        app.state.energy_chat_runtime = EnergyChatApplicationRuntime()
        after_restart = client.post(
            "/energy-chat/v2/threads/thread-restart-proof/replay"
        )
    finally:
        app.state.energy_chat_runtime = previous

    assert missing.status_code == 404
    assert missing.json()["detail"]["error"] == "thread_checkpoint_not_found"
    assert created.status_code == 200
    assert after_restart.status_code == 404
    assert after_restart.json()["detail"]["error"] == "thread_checkpoint_not_found"
