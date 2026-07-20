"""M10 course-correction regression tests — verified defects from portfolio audit."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Defect 1-3: Route identity must own execution profile ──────────────────


def test_deterministic_route_ignores_caller_live_profile() -> None:
    """The /v2/chat route must always use deterministic profile,
    regardless of caller-supplied execution_profile."""
    response = client.post(
        "/energy-chat/v2/chat",
        json={
            "user_message": "test deterministic enforcement",
            "execution_profile": "live_bounded",
        },
    )
    assert response.status_code == 200
    body = response.json()
    # Route owns the profile — must report deterministic_local
    assert body["served_provider"] == "deterministic_local"
    assert body["served_model"] == "energy-chat-template-v1"


def test_live_route_ignores_caller_deterministic_profile() -> None:
    """The /v2/chat/live route must always use live_bounded profile,
    regardless of caller-supplied execution_profile."""
    response = client.post(
        "/energy-chat/v2/chat/live",
        json={
            "user_message": "test live enforcement",
            "execution_profile": "deterministic",
        },
    )
    # Route may return 200 (live succeeds with fake credentials in test)
    # or 400 (provider unavailable) — but must not silently run deterministic
    body = response.json()
    if response.status_code == 200:
        assert body["served_provider"] != "deterministic_local"


# ── Defect 4: No silent cross-provider fallback ────────────────────────────


def test_live_route_rejects_kimi_without_explicit_fallback() -> None:
    """Kimi provider must be rejected unless allow_provider_fallback is true."""
    response = client.post(
        "/energy-chat/v2/chat/live",
        json={
            "user_message": "test kimi rejection",
            "provider_preference": "kimi",
            "execution_profile": "live_bounded",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "provider_unavailable"


# ── Defect 6: Reject unknown fields ────────────────────────────────────────


def test_v2_request_rejects_unknown_fields() -> None:
    """V2 request must reject unknown/typo'd fields instead of silently ignoring."""
    response = client.post(
        "/energy-chat/v2/chat",
        json={
            "user_message": "test",
            "typoed_field": "should be rejected",
        },
    )
    assert response.status_code == 422


# ── Defect 7: auto must not silently map without calibration ───────────────


def test_auto_provider_is_rejected_on_live_without_calibration() -> None:
    """auto provider_preference must fail when no calibrated routing evals exist."""
    response = client.post(
        "/energy-chat/v2/chat/live",
        json={
            "user_message": "test auto rejection",
            "provider_preference": "auto",
            "execution_profile": "live_bounded",
        },
    )
    # auto routing is not calibrated — must fail
    assert response.status_code in (400, 422)


# ── Defect 8: Awaiting-evidence must not report false provider ─────────────


def test_awaiting_evidence_response_is_honest_about_no_provider() -> None:
    """Awaiting-evidence responses must not fabricate served provider/model info."""
    response = client.post(
        "/energy-chat/v2/chat",
        json={
            "user_message": "what is the latest DeepSeek pricing as of today?",
            "mode": "research",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["awaiting_evidence"] is True
    # No candidate was generated, so no provider was called
    assert body["candidate_count"] == 0


# ── M11 wiring: V2 deterministic route uses checkpointing ──────────────────


def test_v2_deterministic_route_replay_is_idempotent() -> None:
    """The deterministic V2 route must use checkpointing so replay with the
    same thread_id returns the same result without duplicate work."""
    response1 = client.post(
        "/energy-chat/v2/chat",
        json={
            "user_message": "Explain the graph backbone architecture.",
            "thread_id": "thread-replay-v2",
        },
    )
    assert response1.status_code == 200
    body1 = response1.json()

    # Replay with same thread_id
    response2 = client.post(
        "/energy-chat/v2/chat",
        json={
            "user_message": "Explain the graph backbone architecture.",
            "thread_id": "thread-replay-v2",
        },
    )
    assert response2.status_code == 200
    body2 = response2.json()

    # Same ledger entries, same final answer
    assert body1["ledger_entry_ids"] == body2["ledger_entry_ids"]
    assert body1["final_answer"] == body2["final_answer"]
    assert body1["candidate_count"] == body2["candidate_count"]


# ── M16: V2 demo route ────────────────────────────────────────────────────


def test_v2_demo_route_is_registered() -> None:
    """The V2 graph-backed demo must be served at /energy-chat/v2/demo."""
    response = client.get("/energy-chat/v2/demo")
    assert response.status_code == 200
    assert "EACHAT V2" in response.text
    assert "Graph-Backed Demo" in response.text
