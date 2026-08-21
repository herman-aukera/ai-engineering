from app.estimator.production_app import create_production_app


def test_estimator_production_surface_exposes_only_current_product_api() -> None:
    app = create_production_app()
    route_paths = {getattr(route, "path", "") for route in app.routes}
    schema_paths = set(app.openapi().get("paths", {}))

    assert "/api/v1/estimate/graph/unified" in route_paths
    assert "/api/v1/estimate/graph/unified/readiness" in route_paths
    assert "/startup" in route_paths
    assert "/health" in route_paths
    assert "/ready" in route_paths
    assert "/version" in route_paths

    for forbidden in (
        "/demo",
        "/sse-demo",
        "/embeddings",
        "/search",
        "/api/v2/estimate",
        "/api/v1/estimate/graph/reviewed/start",
    ):
        assert forbidden not in route_paths

    assert schema_paths
    assert all(path.startswith("/api/v1/estimate/graph/unified") for path in schema_paths)


def test_estimator_operational_probes_are_not_public_business_schema() -> None:
    schema_paths = set(create_production_app().openapi().get("paths", {}))

    assert "/startup" not in schema_paths
    assert "/health" not in schema_paths
    assert "/ready" not in schema_paths
    assert "/version" not in schema_paths
