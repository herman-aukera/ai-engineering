from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_production_ingress_is_immutable_and_body_bounded() -> None:
    base = ROOT / "deploy" / "eacode" / "session15"
    compose = (base / "docker-compose.production.yml").read_text(encoding="utf-8")
    caddy = (base / "Caddyfile").read_text(encoding="utf-8")

    assert "caddy:2.11.4-alpine@sha256:5f5c8640aae01df9654968d946d8f1a56c497f1dd5c5cda4cf95ab7c14d58648" in compose
    assert "request_body" in caddy
    assert "max_size 2MB" in caddy
