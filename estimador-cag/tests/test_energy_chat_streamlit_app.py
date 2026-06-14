from __future__ import annotations

from pathlib import Path
from typing import Any

import energy_chat_streamlit_app as energy_ui

STREAMLIT_SOURCE = Path("energy_chat_streamlit_app.py").read_text(encoding="utf-8")


def test_energy_chat_streamlit_demo_points_to_evaluate_endpoint():
    assert 'ENERGY_CHAT_EVALUATE_PATH = "/energy-chat/evaluate"' in STREAMLIT_SOURCE
    assert "def build_energy_chat_evaluate_url" in STREAMLIT_SOURCE
    assert "def post_energy_chat_evaluation_request" in STREAMLIT_SOURCE


def test_energy_chat_streamlit_demo_exposes_visible_energy_card():
    assert "Energy Card" in STREAMLIT_SOURCE
    assert "Decision" in STREAMLIT_SOURCE
    assert "Energy" in STREAMLIT_SOURCE
    assert "Hard constraints passed" in STREAMLIT_SOURCE
    assert "Remaining caveats" in STREAMLIT_SOURCE


def test_build_energy_chat_payload_uses_chat_lite_by_default():
    payload = energy_ui.build_energy_chat_payload(
        user_message="Check whether this answer satisfies the constraints.",
        draft_answer="The next action is to run the validation gate before claiming success.",
    )

    assert payload == {
        "user_message": "Check whether this answer satisfies the constraints.",
        "draft_answer": "The next action is to run the validation gate before claiming success.",
        "mode": "chat_lite",
    }


def test_format_decision_label_covers_mvp_decisions():
    assert energy_ui.format_decision_label("accept") == "✅ accept"
    assert energy_ui.format_decision_label("repair") == "🛠️ repair"
    assert energy_ui.format_decision_label("reject") == "⛔ reject"
    assert energy_ui.format_decision_label("clarify") == "❓ clarify"


def test_post_energy_chat_evaluation_request_posts_json_payload(monkeypatch):
    captured: dict[str, Any] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            captured["raise_for_status_called"] = True

        def json(self) -> dict[str, Any]:
            return {"decision": "accept"}

    def fake_post(url: str, json: dict[str, Any], timeout: tuple[int, int]) -> FakeResponse:
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(energy_ui.requests, "post", fake_post)
    monkeypatch.setenv("ESTIMADOR_BACKEND_URL", "https://example.test/")

    payload = energy_ui.build_energy_chat_payload(
        user_message="Review this answer.",
        draft_answer="The next action is to run tests.",
    )

    result = energy_ui.post_energy_chat_evaluation_request(payload)

    assert result == {"decision": "accept"}
    assert captured == {
        "url": "https://example.test/energy-chat/evaluate",
        "json": payload,
        "timeout": (10, 120),
        "raise_for_status_called": True,
    }
