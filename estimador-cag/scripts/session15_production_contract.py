"""Deterministic Session 15 production-envelope contract gate.

This check intentionally avoids network/provider calls.  It protects the repository
properties that can regress even when the unit suites remain green: public API
versioning, LLM-free blocking CI, non-root images, and single-ingress production
Compose wiring.
"""

from __future__ import annotations

from pathlib import Path

from app.main import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent


def _read(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"required production-contract file is missing: {path}")
    return path.read_text(encoding="utf-8")


def _check_api_contract() -> None:
    schema = app.openapi()
    paths = schema.get("paths", {})
    required_get_paths = {
        "/health",
        "/ready",
        "/api/v1/estimate/graph/unified/readiness",
    }
    missing = sorted(
        path for path in required_get_paths if "get" not in paths.get(path, {})
    )
    if missing:
        raise AssertionError(f"missing GET production/API contracts: {missing}")

    versioned = [path for path in paths if path.startswith("/api/")]
    non_v1 = sorted(path for path in versioned if not path.startswith("/api/v1/"))
    if non_v1:
        raise AssertionError(f"new /api routes must be major-versioned under /api/v1: {non_v1}")


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
    forbidden = ("OPENAI_API_KEY=", "DEEPSEEK_API_KEY=", "KIMI_API_KEY=")
    if any(value in dockerfile for value in forbidden):
        raise AssertionError("provider secrets/configuration must not be baked into the image")


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
    if "reverse_proxy ai_service:8000" not in caddy:
        raise AssertionError("Caddy must be the single ingress to the private AI service")


def main() -> None:
    _check_api_contract()
    _check_blocking_ci_contract()
    _check_image_contract()
    _check_single_ingress_contract()
    print("session15 production contract: PASS")


if __name__ == "__main__":
    main()
