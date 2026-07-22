"""Product-path contract for the same-origin EACHAT V2 browser client."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_and_demo_open_v2_product_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("EACHAT_V2_ENABLED", "true")

    root = client.get("/", follow_redirects=False)
    demo = client.get("/demo", follow_redirects=False)

    assert root.status_code == 307
    assert demo.status_code == 307
    assert root.headers["location"] == "/energy-chat/v2/demo"
    assert demo.headers["location"] == "/energy-chat/v2/demo"


def test_root_and_demo_roll_back_to_legacy_when_v2_disabled(monkeypatch) -> None:
    monkeypatch.setenv("EACHAT_V2_ENABLED", "false")

    root = client.get("/", follow_redirects=False)
    demo = client.get("/demo", follow_redirects=False)

    assert root.headers["location"] == "/energy-chat/demo"
    assert demo.headers["location"] == "/energy-chat/demo"


def test_v2_product_ui_uses_server_conversations_and_real_graph_endpoints(monkeypatch) -> None:
    monkeypatch.setenv("EACHAT_V2_ENABLED", "true")
    response = client.get("/energy-chat/v2/demo")

    assert response.status_code == 200
    html = response.text
    assert "EACHAT" in html
    assert "/energy-chat/v2/conversations" in html
    assert "/turns" in html
    assert "execution_profile" in html
    assert "live_bounded" in html
    assert "/energy-chat/v2/chat/human" in html
    assert "/energy-chat/v2/threads/${encodeURIComponent(activeGraphThreadId)}/state" in html
    assert "/energy-chat/v2/threads/${encodeURIComponent(activeGraphThreadId)}/replay" in html
    assert "/energy-chat/v2/threads/${encodeURIComponent(activeGraphThreadId)}/resume" in html


def test_v2_product_ui_keeps_only_safe_conversation_index_locally(monkeypatch) -> None:
    monkeypatch.setenv("EACHAT_V2_ENABLED", "true")
    html = client.get("/energy-chat/v2/demo").text

    assert "eachat:v2:conversation-index" in html
    assert "eachat:v2:messages:" not in html
    assert "eachat:v2:threads" not in html
    assert 'class="message user"' in html
    assert 'class="message assistant"' in html
    assert "Server-owned multi-turn history" in html
    assert "Browser storage contains IDs and titles only" in html
    assert "loadConversation" in html
    assert "deleteConversation" in html
    assert "Submit human response" in html
    assert "startHumanFlow" in html
    assert "resumeHumanAction" in html
    assert "inspectThread" in html
    assert "replayThread" in html


def test_v2_product_ui_states_current_runtime_maturity_truthfully(monkeypatch) -> None:
    monkeypatch.setenv("EACHAT_V2_ENABLED", "true")
    html = client.get("/energy-chat/v2/demo").text

    assert "Durable bounded memory" in html
    assert "Critic orchestration" in html
    assert "Committee/adaptive: gated" in html
    assert "context_profile:'balanced'" in html
    assert "Minimal (unsupported)" not in html
    assert "Max (unsupported)" not in html
    assert "Kimi (deferred)" not in html
    assert "OpenAI (deferred)" not in html


def test_v2_replay_uses_dedicated_replay_endpoint_not_chat_reexecution(monkeypatch) -> None:
    monkeypatch.setenv("EACHAT_V2_ENABLED", "true")
    html = client.get("/energy-chat/v2/demo").text

    replay_function = html.split("async function replayThread", maxsplit=1)[1].split(
        "async function inspectThread", maxsplit=1
    )[0]
    assert "/replay" in replay_function
    assert "chat/live" not in replay_function
    assert "user_message" not in replay_function
