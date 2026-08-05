from fastapi.testclient import TestClient

from app.eacode_main import app

client = TestClient(app)


def test_minimal_eacode_composition_root_exposes_only_product_routes() -> None:
    response = client.get("/health")
    paths = {route.path for route in app.routes}

    assert response.status_code == 200
    assert response.json()["product"] == "eacode"
    assert "/eacode/status" in paths
    assert "/eacode/ui" in paths
    assert "/estimate" not in paths
    assert "/sessions" not in paths


def test_minimal_runtime_root_redirects_to_product_ui() -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/eacode/ui"
