"""Deterministic pre-split contract for the EACODE repository."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent

REQUIRED = (
    "README.md",
    ".env.example",
    "app/eacode/production_app.py",
    "app/routers/eacode.py",
    "energy_core/postgres_beta_store.py",
    "energy_core/migrations/0001_eacode_beta_authority.sql",
    "deploy/eacode/Dockerfile",
    "deploy/eacode/session15/docker-compose.production.yml",
    "deploy/eacode/session15/deploy.sh",
    "deploy/eacode/session15/rollback.sh",
    "docs/ARCHITECTURE.md",
    "docs/ENERGY_AWARE_PROTOCOL_V1.md",
    "docs/SECURITY.md",
    "docs/OPERATIONS.md",
    "docs/RELEASE.md",
    "docs/REPO_SPLIT_MANIFEST.md",
)
WORKFLOWS = (
    ".github/workflows/ci.yml",
    ".github/workflows/eacode-postgres-integration.yml",
    ".github/workflows/live-smoke.yml",
    ".github/workflows/eacode-release-image.yml",
)


def verify() -> None:
    missing = [path for path in REQUIRED if not (PROJECT_ROOT / path).is_file()]
    missing += [path for path in WORKFLOWS if not (REPO_ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"EACODE split contract missing files: {missing}")

    production = (PROJECT_ROOT / "app/eacode/production_app.py").read_text(encoding="utf-8")
    for forbidden in ("app.energy_chat", "app.estimator"):
        if forbidden in production:
            raise AssertionError(f"EACODE production depends on peer product: {forbidden}")

    compose = (PROJECT_ROOT / "deploy/eacode/session15/docker-compose.production.yml").read_text(encoding="utf-8")
    if "EACODE_DATABASE_URL:?" not in compose or "EACODE_DEMO_DB_PATH" in compose:
        raise AssertionError("EACODE production authority is not PostgreSQL-only")

    router = (PROJECT_ROOT / "app/routers/eacode.py").read_text(encoding="utf-8")
    if "build_beta_demo_store" not in router:
        raise AssertionError("EACODE beta API bypasses runtime-selected authority store")

    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    for stale in ("Session 07: Embedding pipeline pre-exercise", "Current working branch:"):
        if stale in readme:
            raise AssertionError(f"EACODE README still contains stale coursework state: {stale}")


def main() -> None:
    verify()
    print("EACODE repository split readiness: PASS")


if __name__ == "__main__":
    main()
