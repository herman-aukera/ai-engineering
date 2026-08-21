"""Deterministic Session 15 production-envelope contract for EACODE."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _read(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"required EACODE production-contract file is missing: {path}")
    return path.read_text(encoding="utf-8")


def _paths(app) -> set[str]:
    return {getattr(route, "path", "") for route in app.routes}


def _check_public_contract() -> None:
    from app.eacode.production_app import create_production_app
    from app.main import app as coursework_app

    production_paths = _paths(create_production_app())
    required = {
        "/startup",
        "/health",
        "/ready",
        "/version",
        "/api/v1/eacode/status",
        "/api/v1/eacode/capabilities",
        "/api/v1/eacode/select",
        "/api/v1/eacode/ui",
    }
    missing = sorted(required - production_paths)
    if missing:
        raise AssertionError(f"missing EACODE production routes: {missing}")

    non_v1 = sorted(
        path
        for path in production_paths
        if path.startswith("/api/") and not path.startswith("/api/v1/")
    )
    if non_v1:
        raise AssertionError(f"EACODE production API must be major-versioned: {non_v1}")

    if "/eacode/status" in production_paths:
        raise AssertionError("isolated production app must not publish legacy unversioned EACODE routes")
    if "/eacode/status" not in _paths(coursework_app):
        raise AssertionError("coursework app must preserve the legacy compatibility route")


def _check_ci_separation() -> None:
    ci = _read(REPO_ROOT / ".github" / "workflows" / "ci.yml")
    forbidden = {
        "${{ secrets.": "blocking EACODE CI must not consume provider secrets",
        "energy_core_live_provider_smoke.py": "live-provider smoke belongs to a separate cadence",
        "--live": "blocking EACODE CI must not opt into live model execution",
    }
    failures = [message for needle, message in forbidden.items() if needle in ci]
    if failures:
        raise AssertionError("; ".join(failures))

    live = _read(REPO_ROOT / ".github" / "workflows" / "live-smoke.yml")
    if "workflow_dispatch:" not in live:
        raise AssertionError("EACODE live-provider smoke must remain explicitly dispatched")
    if "energy_core_live_provider_smoke.py" not in live:
        raise AssertionError("EACODE live-provider workflow must own credentialed provider proof")


def _check_image_contract() -> None:
    dockerfile = _read(PROJECT_ROOT / "deploy" / "eacode" / "Dockerfile")
    if "USER eacode" not in dockerfile:
        raise AssertionError("EACODE production image must run as the non-root eacode user")
    if "app.eacode.production_app:app" not in dockerfile:
        raise AssertionError("EACODE image must start the isolated production composition root")
    forbidden = ("OPENAI_API_KEY=", "DEEPSEEK_API_KEY=", "KIMI_API_KEY=")
    if any(marker in dockerfile for marker in forbidden):
        raise AssertionError("provider credentials/configuration must not be baked into EACODE image")


def _check_release_contract() -> None:
    release = _read(REPO_ROOT / ".github" / "workflows" / "eacode-release-image.yml")
    required = (
        "workflow_dispatch:",
        "packages: write",
        "push: true",
        "${{ github.sha }}",
        "steps.image.outputs.digest",
        "org.opencontainers.image.revision",
    )
    missing = [marker for marker in required if marker not in release]
    if missing:
        raise AssertionError(f"EACODE immutable release workflow is missing markers: {missing}")
    if "DEEPSEEK_API_KEY" in release or "KIMI_API_KEY" in release or "OPENAI_API_KEY" in release:
        raise AssertionError("EACODE image release must not require provider credentials")


def _check_single_ingress() -> None:
    base = PROJECT_ROOT / "deploy" / "eacode" / "session15"
    compose = _read(base / "docker-compose.production.yml")
    caddy = _read(base / "Caddyfile")
    if compose.count("ports:") != 1:
        raise AssertionError("EACODE production Compose must expose exactly one host service")
    for forbidden_binding in ("8000:8000", "5432:", "6379:"):
        if forbidden_binding in compose:
            raise AssertionError(f"EACODE production topology exposes internal port {forbidden_binding}")
    if "reverse_proxy eacode:8000" not in caddy or "health_uri /ready" not in caddy:
        raise AssertionError("Caddy must be the readiness-aware single ingress to EACODE")


def _check_deploy_contract() -> None:
    base = PROJECT_ROOT / "deploy" / "eacode" / "session15"
    deploy = _read(base / "deploy.sh")
    rollback = _read(base / "rollback.sh")
    if "@sha256:" not in deploy or "docker build" in deploy:
        raise AssertionError("EACODE deployment must use an immutable digest without rebuilding")
    if "/ready" not in deploy:
        raise AssertionError("EACODE deployment must be readiness-gated")
    if "org.opencontainers.image.revision" not in deploy:
        raise AssertionError("EACODE deployment must derive safe Git SHA release metadata from the image")
    if "ROLLBACK_IMAGE" not in rollback or "@sha256:" not in rollback:
        raise AssertionError("EACODE rollback must use a previous immutable image digest")


def main() -> None:
    _check_public_contract()
    _check_ci_separation()
    _check_image_contract()
    _check_release_contract()
    _check_single_ingress()
    _check_deploy_contract()
    print("eacode session15 production contract: PASS")


if __name__ == "__main__":
    main()
