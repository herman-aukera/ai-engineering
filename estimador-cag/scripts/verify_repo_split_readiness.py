"""Deterministic pre-split contract for the EACHAT repository."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent

REQUIRED = (
    "README.md",
    ".env.example",
    "app/energy_chat/production_app.py",
    "app/energy_chat/production_router.py",
    "deploy/eachat/Dockerfile",
    "deploy/eachat/session15/docker-compose.production.yml",
    "deploy/eachat/session15/deploy.sh",
    "deploy/eachat/session15/rollback.sh",
    "docs/ARCHITECTURE.md",
    "docs/ENERGY_AWARE_PROTOCOL_V1.md",
    "docs/SECURITY.md",
    "docs/OPERATIONS.md",
    "docs/RELEASE.md",
    "docs/REPO_SPLIT_MANIFEST.md",
)
WORKFLOWS = (
    ".github/workflows/energy-chat-ci.yml",
    ".github/workflows/eachat-container-canary.yml",
    ".github/workflows/eachat-live-provider-smoke.yml",
    ".github/workflows/eachat-release-image.yml",
)


def verify() -> None:
    missing = [path for path in REQUIRED if not (PROJECT_ROOT / path).is_file()]
    missing += [path for path in WORKFLOWS if not (REPO_ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"EACHAT split contract missing files: {missing}")

    production = (PROJECT_ROOT / "app/energy_chat/production_app.py").read_text(encoding="utf-8")
    transport = (PROJECT_ROOT / "app/energy_chat/production_router.py").read_text(encoding="utf-8")
    for forbidden in ("app.estimator", "app.eacode"):
        if forbidden in production or forbidden in transport:
            raise AssertionError(f"EACHAT production depends on peer product: {forbidden}")
    if "from app.energy_chat.router import" in transport:
        raise AssertionError("EACHAT production transport still depends on legacy evaluation router")

    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    for stale in ("incubator branch", "Current working branch:", "Official delivery alias branch"):
        if stale in readme:
            raise AssertionError(f"EACHAT README still contains stale coursework state: {stale}")


def main() -> None:
    verify()
    print("EACHAT repository split readiness: PASS")


if __name__ == "__main__":
    main()
