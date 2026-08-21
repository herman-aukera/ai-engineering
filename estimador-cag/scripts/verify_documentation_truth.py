"""Fail when canonical product documentation drifts from executable product truth."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "docs" / "energy_aware_product_manifest.json").read_text(encoding="utf-8"))

STALE_CLAIMS = (
    "authenticated tenant/thread ownership",
    "multi-tenant identity/ownership",
    "isolated product dependency lock/minimal runtime dependency set rather than",
    "Milestone 11 is next",
    "Status: draft, open, unmerged",
)


def verify() -> dict[str, object]:
    lower = README.casefold()
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
    missing = [value for value in required if value not in README]
    if missing:
        raise AssertionError(f"README is missing current executable product truth: {missing}")
    stale = [value for value in STALE_CLAIMS if value.casefold() in lower]
    if stale:
        raise AssertionError(f"README contains stale blocker/history claims: {stale}")
    if "not yet" not in lower or "production-ready" not in lower:
        raise AssertionError("README must preserve an explicit non-production-ready claim boundary")

    return {
        "product": product,
        "canonical_branch": branch,
        "protocol_version": MANIFEST["protocol_version"],
        "checked_markers": len(required),
        "stale_claim_count": 0,
        "status": "pass",
    }


def main() -> None:
    print(json.dumps(verify(), sort_keys=True))


if __name__ == "__main__":
    main()
