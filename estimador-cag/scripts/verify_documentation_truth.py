"""Fail when canonical product documentation drifts from executable product truth."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
SECURITY = (ROOT / "docs" / "SECURITY.md").read_text(encoding="utf-8")
MANIFEST = json.loads(
    (ROOT / "docs" / "energy_aware_product_manifest.json").read_text(encoding="utf-8")
)

README_STALE_CLAIMS = (
    "authenticated tenant/thread ownership",
    "multi-tenant identity/ownership",
    "isolated product dependency lock/minimal runtime dependency set rather than",
    "Milestone 11 is next",
    "Status: draft, open, unmerged",
)
SECURITY_STALE_CLAIMS = (
    "does not yet prove a complete tenant/actor ownership boundary",
    "add authenticated actor/tenant context and bind every persisted estimation/thread",
)
SECURITY_REQUIRED_CLAIMS = (
    "signed actor/session identity",
    "PostgreSQL ownership",
    "inspect/resume operations enforce that ownership boundary",
    "external authentication/OIDC",
)


def _missing(document: str, values: tuple[str, ...]) -> list[str]:
    return [value for value in values if value.casefold() not in document.casefold()]


def _present(document: str, values: tuple[str, ...]) -> list[str]:
    return [value for value in values if value.casefold() in document.casefold()]


def verify() -> dict[str, object]:
    product = str(MANIFEST["product"])
    branch = str(MANIFEST["canonical_branch"])
    surface = str(MANIFEST["public_surface"])
    surface_anchor = surface.rsplit("/", 1)[0]
    dependency_root = str(MANIFEST["dependency_lock"]).rsplit("/", 1)[0]

    required = (
        branch,
        surface_anchor,
        dependency_root,
        "docs/energy_aware_product_manifest.json",
        "scripts/verify_energy_aware_protocol.py",
        "scripts/product_split_dry_run.py",
        "energy-aware.event.v1",
        "PostgreSQL",
    )
    missing = _missing(README, required)
    if missing:
        raise AssertionError(f"README is missing current executable product truth: {missing}")
    stale = _present(README, README_STALE_CLAIMS)
    if stale:
        raise AssertionError(f"README contains stale blocker/history claims: {stale}")
    if "not yet" not in README.casefold() or "production-ready" not in README.casefold():
        raise AssertionError("README must preserve an explicit non-production-ready claim boundary")

    security_missing = _missing(SECURITY, SECURITY_REQUIRED_CLAIMS)
    if security_missing:
        raise AssertionError(
            f"SECURITY.md is missing current ownership/claim-boundary truth: {security_missing}"
        )
    security_stale = _present(SECURITY, SECURITY_STALE_CLAIMS)
    if security_stale:
        raise AssertionError(f"SECURITY.md contains stale ownership blockers: {security_stale}")

    return {
        "product": product,
        "canonical_branch": branch,
        "protocol_version": MANIFEST["protocol_version"],
        "checked_readme_markers": len(required),
        "checked_security_markers": len(SECURITY_REQUIRED_CLAIMS),
        "stale_claim_count": 0,
        "status": "pass",
    }


def main() -> None:
    print(json.dumps(verify(), sort_keys=True))


if __name__ == "__main__":
    main()
