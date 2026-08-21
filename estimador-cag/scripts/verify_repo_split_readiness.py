"""Deterministic pre-split contract for the Energy-Aware Estimator repository."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent

REQUIRED = (
    "README.md",
    ".env.example",
    "Dockerfile",
    "app/estimator/production_app.py",
    "deploy/session15/docker-compose.production.yml",
    "deploy/session15/deploy.sh",
    "deploy/session15/rollback.sh",
    "docs/ARCHITECTURE.md",
    "docs/ENERGY_AWARE_PROTOCOL_V1.md",
    "docs/SECURITY.md",
    "docs/OPERATIONS.md",
    "docs/RELEASE.md",
    "docs/REPO_SPLIT_MANIFEST.md",
    "tests/smoke/test_session15_http_smoke.py",
)
WORKFLOWS = (
    ".github/workflows/ci.yml",
    ".github/workflows/provider-evaluation.yml",
    ".github/workflows/release-image.yml",
)


def verify() -> None:
    missing = [path for path in REQUIRED if not (PROJECT_ROOT / path).is_file()]
    missing += [path for path in WORKFLOWS if not (REPO_ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"estimator split contract missing files: {missing}")

    production = (PROJECT_ROOT / "app/estimator/production_app.py").read_text(encoding="utf-8")
    for forbidden in ("app.energy_chat", "app.eacode"):
        if forbidden in production:
            raise AssertionError(f"estimator production root depends on peer product: {forbidden}")

    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    if "app.estimator.production_app:app" not in dockerfile:
        raise AssertionError("Dockerfile does not start isolated estimator production app")

    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    for stale in ("Current consolidation candidate", "Draft PR: #21", "Status: draft, open, unmerged"):
        if stale in readme:
            raise AssertionError(f"README still contains stale consolidation instruction: {stale}")


def main() -> None:
    verify()
    print("estimator repository split readiness: PASS")


if __name__ == "__main__":
    main()
