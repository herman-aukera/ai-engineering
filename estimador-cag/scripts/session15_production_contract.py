"""Deterministic production-envelope contract for the canonical estimator service."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _read(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"required production-contract file is missing: {path}")
    return path.read_text(encoding="utf-8")


def _check_api_contract() -> None:
    from app.estimator.production_app import create_production_app

    app = create_production_app()
    paths = app.openapi().get("paths", {})
    if not paths:
        raise AssertionError("estimator production API has no public business routes")
    noncanonical = sorted(
        path for path in paths if not path.startswith("/api/v1/estimate/graph/unified")
    )
    if noncanonical:
        raise AssertionError(
            f"estimator production app exposes noncanonical business routes: {noncanonical}"
        )
    required = {
        "/api/v1/estimate/graph/unified",
        "/api/v1/estimate/graph/unified/readiness",
    }
    missing = sorted(required - set(paths))
    if missing:
        raise AssertionError(f"missing canonical estimator routes: {missing}")

    route_paths = {getattr(route, "path", "") for route in app.routes}
    for forbidden in ("/demo", "/sse-demo", "/embeddings", "/search", "/api/v2/estimate"):
        if forbidden in route_paths:
            raise AssertionError(f"historical/coursework route leaked into production: {forbidden}")

    source = _read(PROJECT_ROOT / "app" / "estimator" / "production_app.py")
    required_security = (
        "ESTIMATOR_SESSION_SIGNING_KEY",
        "PostgresEstimationOwnershipStore",
        "Depends(require_actor)",
    )
    missing_security = [marker for marker in required_security if marker not in source]
    if missing_security:
        raise AssertionError(
            f"estimator identity/ownership contract missing markers: {missing_security}"
        )


def _check_blocking_ci_contract() -> None:
    ci = _read(REPO_ROOT / ".github" / "workflows" / "ci.yml")
    forbidden = {
        "${{ secrets.": "blocking CI must not consume repository/provider secrets",
        "provider_readiness_benchmark.py": "live provider benchmark belongs to a separate cadence",
        "-m live_provider": "live provider tests belong to a separate cadence",
    }
    failures = [message for needle, message in forbidden.items() if needle in ci]
    if failures:
        raise AssertionError("; ".join(failures))

    live = _read(REPO_ROOT / ".github" / "workflows" / "provider-evaluation.yml")
    if "workflow_dispatch:" not in live:
        raise AssertionError("provider evaluation must remain explicitly/manual dispatched")
    if "provider_readiness_benchmark.py" not in live:
        raise AssertionError("provider benchmark must live in the non-blocking evaluation workflow")


def _check_image_contract() -> None:
    dockerfile = _read(PROJECT_ROOT / "Dockerfile")
    if "USER app" not in dockerfile:
        raise AssertionError("production image must run as the non-root app user")
    if "app.estimator.production_app:app" not in dockerfile:
        raise AssertionError("production image must start the isolated estimator composition root")
    if "app.main:app" in dockerfile:
        raise AssertionError("production image must not start the broad coursework application")
    forbidden = ("OPENAI_API_KEY=", "DEEPSEEK_API_KEY=", "KIMI_API_KEY=")
    if any(value in dockerfile for value in forbidden):
        raise AssertionError("provider secrets/configuration must not be baked into the image")


def _check_release_contract() -> None:
    release = _read(REPO_ROOT / ".github" / "workflows" / "release-image.yml")
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
        raise AssertionError(f"immutable release workflow is missing markers: {missing}")
    if "OPENAI_API_KEY" in release or "DEEPSEEK_API_KEY" in release or "KIMI_API_KEY" in release:
        raise AssertionError("image release must not require provider credentials")


def _check_single_ingress_contract() -> None:
    compose = _read(PROJECT_ROOT / "deploy" / "session15" / "docker-compose.production.yml")
    caddy = _read(PROJECT_ROOT / "deploy" / "session15" / "Caddyfile")
    if compose.count("ports:") != 1:
        raise AssertionError("production Compose must expose exactly one service to the host")
    for forbidden_binding in ("5432:", "6379:", "8000:8000"):
        if forbidden_binding in compose:
            raise AssertionError(
                f"production Compose exposes an internal service/port: {forbidden_binding}"
            )
    if "ESTIMATOR_SESSION_SIGNING_KEY:?" not in compose:
        raise AssertionError("production Compose must require signed estimator identity")
    if "ESTIMATOR_ALLOW_IN_MEMORY_OWNERSHIP" in compose:
        raise AssertionError("production Compose must not enable process-local ownership")
    if "reverse_proxy ai_service:8000" not in caddy or "health_uri /ready" not in caddy:
        raise AssertionError("Caddy must be the readiness-aware single ingress to the private estimator")


def _check_deploy_contract() -> None:
    deploy = _read(PROJECT_ROOT / "deploy" / "session15" / "deploy.sh")
    rollback = _read(PROJECT_ROOT / "deploy" / "session15" / "rollback.sh")
    if "@sha256:" not in deploy or "docker compose" not in deploy:
        raise AssertionError("deployment must require and deploy an immutable image digest")
    if "docker build" in deploy:
        raise AssertionError("deployment must not rebuild the application artifact")
    if "/ready" not in deploy:
        raise AssertionError("deployment must be gated on readiness")
    if "org.opencontainers.image.revision" not in deploy:
        raise AssertionError("deployment must derive safe Git SHA release metadata from the image")
    if "ROLLBACK_IMAGE" not in rollback or "@sha256:" not in rollback:
        raise AssertionError("rollback must require a previous immutable image digest")


def main() -> None:
    _check_api_contract()
    _check_blocking_ci_contract()
    _check_image_contract()
    _check_release_contract()
    _check_single_ingress_contract()
    _check_deploy_contract()
    print("estimator production contract: PASS")


if __name__ == "__main__":
    main()
