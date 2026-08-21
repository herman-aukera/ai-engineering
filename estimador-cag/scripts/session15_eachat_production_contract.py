"""Deterministic production-envelope contract for the canonical EACHAT service."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _read(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"required EACHAT production-contract file is missing: {path}")
    return path.read_text(encoding="utf-8")


def _route_paths() -> set[str]:
    from app.energy_chat.production_app import create_production_app

    return {getattr(route, "path", "") for route in create_production_app().routes}


def _check_public_contract() -> None:
    paths = _route_paths()
    required = {
        "/startup",
        "/health",
        "/ready",
        "/version",
        "/energy-chat/v2/chat",
        "/energy-chat/v2/chat/live",
        "/energy-chat/v2/demo",
        "/energy-chat/v2/conversations",
        "/energy-chat/v2/chat/human",
    }
    missing = sorted(required - paths)
    if missing:
        raise AssertionError(f"missing EACHAT production routes: {missing}")

    legacy = sorted(
        path
        for path in paths
        if path.startswith("/energy-chat/") and not path.startswith("/energy-chat/v2/")
    )
    if legacy:
        raise AssertionError(f"legacy evaluation/coursework routes leaked into production: {legacy}")


def _check_ci_separation() -> None:
    ci = _read(REPO_ROOT / ".github" / "workflows" / "energy-chat-ci.yml")
    forbidden = {
        "${{ secrets.": "blocking EACHAT CI must not consume provider secrets",
        "smoke_eachat_live_provider.py": "live provider smoke belongs to a separate cadence",
        "--live": "blocking EACHAT CI must not enable live provider mode",
    }
    failures = [message for needle, message in forbidden.items() if needle in ci]
    if failures:
        raise AssertionError("; ".join(failures))

    live = _read(REPO_ROOT / ".github" / "workflows" / "eachat-live-provider-smoke.yml")
    if "workflow_dispatch:" not in live:
        raise AssertionError("EACHAT live-provider smoke must remain explicitly dispatched")
    if "smoke_eachat_live_provider.py" not in live or "--live" not in live:
        raise AssertionError("EACHAT live-provider workflow must own the credentialed call")


def _check_image_contract() -> None:
    dockerfile = _read(PROJECT_ROOT / "deploy" / "eachat" / "Dockerfile")
    if "USER eachat" not in dockerfile:
        raise AssertionError("EACHAT production image must run as the non-root eachat user")
    if "app.energy_chat.production_app:app" not in dockerfile:
        raise AssertionError("EACHAT image must start the isolated production composition root")


def _check_release_contract() -> None:
    release = _read(REPO_ROOT / ".github" / "workflows" / "eachat-release-image.yml")
    required = (
        "workflow_dispatch:",
        "packages: write",
        "push: true",
        "${{ github.sha }}",
        "steps.build.outputs.digest",
        "org.opencontainers.image.revision",
    )
    missing = [marker for marker in required if marker not in release]
    if missing:
        raise AssertionError(f"EACHAT immutable release workflow is missing markers: {missing}")
    if "OPENAI_API_KEY" in release or "DEEPSEEK_API_KEY" in release or "KIMI_API_KEY" in release:
        raise AssertionError("EACHAT image release must not require provider credentials")


def _check_single_ingress() -> None:
    base = PROJECT_ROOT / "deploy" / "eachat" / "session15"
    compose = _read(base / "docker-compose.production.yml")
    caddy = _read(base / "Caddyfile")
    if compose.count("ports:") != 1:
        raise AssertionError("EACHAT production Compose must expose exactly one host service")
    for forbidden_binding in ("5432:", "6379:", "8000:8000"):
        if forbidden_binding in compose:
            raise AssertionError(f"EACHAT production topology exposes internal port {forbidden_binding}")
    if "reverse_proxy eachat:8000" not in caddy or "health_uri /ready" not in caddy:
        raise AssertionError("Caddy must be the readiness-aware single ingress to EACHAT")


def _check_durable_runtime_contract() -> None:
    compose = _read(
        PROJECT_ROOT / "deploy" / "eachat" / "session15" / "docker-compose.production.yml"
    )
    if "EACHAT_ALLOW_IN_MEMORY" in compose:
        raise AssertionError("production topology must not enable process-local authoritative state")
    required = ("EACHAT_POSTGRES_URL:?", "EACHAT_MEMORY_ENCRYPTION_KEY:?")
    if any(marker not in compose for marker in required):
        raise AssertionError("production topology must require durable encrypted conversation state")


def _check_deploy_contract() -> None:
    base = PROJECT_ROOT / "deploy" / "eachat" / "session15"
    deploy = _read(base / "deploy.sh")
    rollback = _read(base / "rollback.sh")
    if "@sha256:" not in deploy or "docker build" in deploy:
        raise AssertionError("EACHAT deployment must use an immutable digest without rebuilding")
    if "/ready" not in deploy:
        raise AssertionError("EACHAT deployment must be readiness-gated")
    if "org.opencontainers.image.revision" not in deploy:
        raise AssertionError("EACHAT deployment must derive safe Git SHA release metadata from the image")
    if "ROLLBACK_IMAGE" not in rollback or "@sha256:" not in rollback:
        raise AssertionError("EACHAT rollback must use the previous immutable digest")


def main() -> None:
    _check_public_contract()
    _check_ci_separation()
    _check_image_contract()
    _check_release_contract()
    _check_single_ingress()
    _check_durable_runtime_contract()
    _check_deploy_contract()
    print("eachat production contract: PASS")


if __name__ == "__main__":
    main()
