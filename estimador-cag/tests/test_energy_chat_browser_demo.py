from fastapi.testclient import TestClient

from app.main import app


def test_energy_chat_browser_demo_route_serves_same_origin_ui() -> None:
    client = TestClient(app)

    response = client.get("/energy-chat/demo")

    assert response.status_code == 200
    assert "Energy Aware Chat MVP Demo" in response.text
    assert "/energy-chat/rag/search" in response.text
    assert "/energy-chat/chat" in response.text
    assert "/energy-chat/benchmark/deepseek-energy-aware" in response.text
    assert "Energy Card" in response.text


def test_energy_chat_browser_demo_explains_execution_and_benchmark_boundaries() -> None:
    client = TestClient(app)

    response = client.get("/energy-chat/demo")

    assert response.status_code == 200
    assert "Visible execution audit" in response.text
    assert "provider draft call" in response.text
    assert "Run measurement benchmark" in response.text
    assert "quality-improvement claim" in response.text
