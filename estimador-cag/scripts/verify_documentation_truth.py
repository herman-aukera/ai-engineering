"""Fail when canonical product documentation drifts from executable product truth."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
README = (ROOT / "README.md").read_text(encoding="utf-8")
SECURITY = (DOCS / "SECURITY.md").read_text(encoding="utf-8")
PROVIDER_SPEC = (DOCS / "energy_aware_chat_provider_context_spec.md").read_text(
    encoding="utf-8"
)
PROVIDER_FACT_AUDIT = (
    DOCS / "energy_aware_chat_provider_fact_audit_2026-08-23.md"
).read_text(encoding="utf-8")
PROVIDER_CATALOG = (ROOT / "app" / "energy_chat" / "provider_catalog.py").read_text(
    encoding="utf-8"
)
MANIFEST = json.loads(
    (DOCS / "energy_aware_product_manifest.json").read_text(encoding="utf-8")
)

README_STALE_CLAIMS = (
    "authenticated tenant/thread ownership",
    "multi-tenant identity/ownership",
    "isolated product dependency lock/minimal runtime dependency set rather than",
    "Milestone 11 is next",
    "Status: draft, open, unmerged",
)
SECURITY_STALE_CLAIMS = (
    "not yet bound to a fully authenticated tenant/actor ownership model",
    "introduce an IdentityProvider boundary and persist owner/tenant identity",
)
SECURITY_REQUIRED_CLAIMS = (
    "signed actor/session identity",
    "PostgreSQL ownership",
    "read/replay/resume/delete operations enforce owner",
    "external authentication/OIDC",
)
PROVIDER_REQUIRED_CLAIMS = (
    (
        "provider specification",
        PROVIDER_SPEC,
        "Provider catalog/adapters, strict provider routing, and request-scoped BYOK are implemented",
    ),
    ("provider specification", PROVIDER_SPEC, "catalog version: 2.1.0"),
    ("provider specification", PROVIDER_SPEC, "verified at:     2026-08-23"),
    ("provider specification", PROVIDER_SPEC, "review by:       2026-09-22"),
    (
        "provider specification",
        PROVIDER_SPEC,
        "fail-closed temporal fact-review deadline",
    ),
    ("provider fact audit", PROVIDER_FACT_AUDIT, "catalog `2.1.0`"),
    (
        "provider fact audit",
        PROVIDER_FACT_AUDIT,
        "must be re-audited no later than `2026-09-22`",
    ),
    ("provider catalog", PROVIDER_CATALOG, 'CATALOG_VERSION = "2.1.0"'),
    (
        "provider catalog",
        PROVIDER_CATALOG,
        'CATALOG_VERIFIED_AT = "2026-08-23"',
    ),
    (
        "provider catalog",
        PROVIDER_CATALOG,
        'CATALOG_REVIEW_BY = "2026-09-22"',
    ),
    ("provider catalog", PROVIDER_CATALOG, "def assert_catalog_fresh("),
)
PROVIDER_STALE_CLAIMS = (
    (
        "provider specification",
        PROVIDER_SPEC,
        "implementation pending dedicated milestones",
    ),
    (
        "provider specification",
        PROVIDER_SPEC,
        "Not yet treated as verified by this repository",
    ),
    (
        "provider specification",
        PROVIDER_SPEC,
        "exact API model ID must be verified",
    ),
)


def _normalize(document: str) -> str:
    """Normalize presentation whitespace without weakening textual claim matching."""

    return " ".join(document.casefold().split())


def _contains(document: str, value: str) -> bool:
    return _normalize(value) in _normalize(document)


def _missing(document: str, values: tuple[str, ...]) -> list[str]:
    return [value for value in values if not _contains(document, value)]


def _present(document: str, values: tuple[str, ...]) -> list[str]:
    return [value for value in values if _contains(document, value)]


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
        raise AssertionError(
            f"README is missing current executable product truth: {missing}"
        )
    stale = _present(README, README_STALE_CLAIMS)
    if stale:
        raise AssertionError(f"README contains stale blocker/history claims: {stale}")
    if "not yet" not in README.casefold() or "production-ready" not in README.casefold():
        raise AssertionError(
            "README must preserve an explicit non-production-ready claim boundary"
        )

    security_missing = _missing(SECURITY, SECURITY_REQUIRED_CLAIMS)
    if security_missing:
        raise AssertionError(
            f"SECURITY.md is missing current ownership/claim-boundary truth: {security_missing}"
        )
    security_stale = _present(SECURITY, SECURITY_STALE_CLAIMS)
    if security_stale:
        raise AssertionError(f"SECURITY.md contains stale ownership blockers: {security_stale}")

    provider_missing = [
        f"{name}: {marker}"
        for name, document, marker in PROVIDER_REQUIRED_CLAIMS
        if not _contains(document, marker)
    ]
    if provider_missing:
        raise AssertionError(
            "Provider documentation/catalog truth is incomplete: "
            f"{provider_missing}"
        )

    provider_stale = [
        f"{name}: {marker}"
        for name, document, marker in PROVIDER_STALE_CLAIMS
        if _contains(document, marker)
    ]
    if provider_stale:
        raise AssertionError(
            "Canonical provider documentation contains stale claims: "
            f"{provider_stale}"
        )

    return {
        "product": product,
        "canonical_branch": branch,
        "protocol_version": MANIFEST["protocol_version"],
        "checked_readme_markers": len(required),
        "checked_security_markers": len(SECURITY_REQUIRED_CLAIMS),
        "checked_provider_markers": len(PROVIDER_REQUIRED_CLAIMS),
        "stale_claim_count": 0,
        "status": "pass",
    }


def main() -> None:
    print(json.dumps(verify(), sort_keys=True))


if __name__ == "__main__":
    main()
