from app.energy_chat.production_app import create_production_app


def test_eachat_production_surface_is_v2_only() -> None:
    app = create_production_app()
    paths = {getattr(route, "path", "") for route in app.routes}

    required = {
        "/energy-chat/v2/chat",
        "/energy-chat/v2/chat/live",
        "/energy-chat/v2/threads/{thread_id}/state",
        "/energy-chat/v2/threads/{thread_id}/replay",
        "/energy-chat/v2/conversations",
        "/energy-chat/v2/chat/human",
        "/energy-chat/v2/threads/{thread_id}/resume",
        "/energy-chat/v2/demo",
    }
    assert required.issubset(paths)

    forbidden = {
        "/energy-chat/evaluate",
        "/energy-chat/evaluate/repair-once",
        "/energy-chat/source-needed",
        "/energy-chat/evidence/bundle",
        "/energy-chat/rag/search",
        "/energy-chat/chat",
        "/energy-chat/chat/live",
        "/energy-chat/draft/deepseek-baseline",
        "/energy-chat/benchmark/deepseek-energy-aware",
        "/energy-chat/benchmark/fixed",
        "/energy-chat/benchmark/fixed/report",
    }
    assert not forbidden.intersection(paths)


def test_eachat_public_schema_contains_only_v2_business_contracts() -> None:
    schema_paths = set(create_production_app().openapi().get("paths", {}))

    assert schema_paths
    assert all(path.startswith("/energy-chat/v2/") for path in schema_paths)
