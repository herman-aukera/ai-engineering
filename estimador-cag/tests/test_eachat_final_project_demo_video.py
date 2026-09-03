from pathlib import Path

DEMO_SCRIPT = Path("docs/final_project/DEMO_VIDEO_SCRIPT.md")


def test_final_project_demo_script_covers_the_required_three_minute_story() -> None:
    assert DEMO_SCRIPT.is_file()
    script = DEMO_SCRIPT.read_text(encoding="utf-8")

    for timestamp in (
        "0:00–0:20",
        "0:20–0:45",
        "0:45–1:30",
        "1:30–1:55",
        "1:55–2:15",
        "2:15–2:35",
        "2:35–2:50",
        "2:50–3:00",
    ):
        assert timestamp in script

    for proof in (
        "/energy-chat/v2/chat",
        "/energy-chat/v2/monitoring/dashboard",
        "PostgreSQL connections are exhausted",
        "Spring Boot 2.7.18",
        "Patch the Java source code",
        "retrieval_hit_rate",
        "finalproject-GG",
        "public URL or uploaded video",
    ):
        assert proof in script


def test_demo_script_keeps_credentials_and_unverified_claims_out_of_the_recording() -> None:
    script = DEMO_SCRIPT.read_text(encoding="utf-8")

    assert "Do not show provider keys" in script
    assert "LIVE-VERIFIED only if" in script
    assert "production-ready" in script
    assert "Copy only the token" in script
