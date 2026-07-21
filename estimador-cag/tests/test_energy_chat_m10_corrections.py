"""M10 course-correction regression tests — verified defects from portfolio audit."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Defect 1-3: Route identity must own execution profile ──────────────────


def test_deterministic_route_rejects_caller_live_profile() -> None:
    """The deterministic route must reject a contradictory live declaration."""

    response = client.post(
        "/energy-chat/v2/chat",
        json={
            "user_message": "test deterministic enforcement",
            "execution_profile": "live_bounded",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "unsupported_execution_profile"


def test_live_route_rejects_caller_deterministic_profile() -> None:
    """The live route must reject a contradictory deterministic declaration."""

    response = client.post(
        "/energy-chat/v2/chat/live",
        json={
            "user_message": "test live enforcement",
            "execution_profile": "deterministic",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "unsupported_execution_profile"


# ── Defect 4: No silent cross-provider fallback ────────────────────────────


def test_live_route_rejects_kimi_without_explicit_fallback() -> None:
    """Direct Kimi selection remains unavailable until its adapter is enabled."""

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
    """V2 request must reject unknown fields instead of silently ignoring them."""

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
    """Automatic routing must fail when no calibrated routing evaluation exists."""

    response = client.post(
        "/energy-chat/v2/chat/live",
        json={
            "user_message": "test auto rejection",
            "provider_preference": "auto",
            "execution_profile": "live_bounded",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "provider_unavailable"


# ── Defect 8: Awaiting-evidence must not report false provider ─────────────


def test_awaiting_evidence_response_is_honest_about_no_provider() -> None:
    """Awaiting-evidence responses must not fabricate provider information."""

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
    assert body["candidate_count"] == 0
    assert body["served_provider"] == "none"
    assert body["served_model"] is None
    assert body["provider_metrics_summary"]["provider_call_count"] == 0


# ── M11 wiring: current route behavior is deterministic, not replay proof ──


def test_v2_deterministic_route_repeated_request_is_stable() -> None:
    """Repeated deterministic requests are stable; checkpoint replay is tested later."""

    response1 = client.post(
        "/energy-chat/v2/chat",
        json={
            "user_message": "Explain the graph backbone architecture.",
            "thread_id": "thread-replay-v2",
        },
    )
    response2 = client.post(
        "/energy-chat/v2/chat",
        json={
            "user_message": "Explain the graph backbone architecture.",
            "thread_id": "thread-replay-v2",
        },
    )

    assert response1.status_code == 200
    assert response2.status_code == 200
    body1 = response1.json()
    body2 = response2.json()
    assert body1["final_answer"] == body2["final_answer"]
    assert body1["candidate_count"] == body2["candidate_count"]
    assert body1["final_disposition"] == body2["final_disposition"]


# ── M16: V2 demo route ────────────────────────────────────────────────────


def test_v2_demo_route_is_registered() -> None:
    """The V2 graph-backed demo must be served at /energy-chat/v2/demo."""

    response = client.get("/energy-chat/v2/demo")
    assert response.status_code == 200
    assert "EACHAT V2" in response.text
    assert "Graph-Backed Demo" in response.text
