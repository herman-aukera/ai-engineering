"""Evaluate the three canonical Energy-Aware products as peer repositories."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

CONTRACT_SCRIPTS = (
    "verify_energy_aware_protocol.py",
    "verify_documentation_truth.py",
    "product_split_dry_run.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_contract(root: Path, script: str) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, str(root / "scripts" / script)],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout.strip().splitlines()[-1])


def _verify_lock(root: Path, manifest: dict[str, object]) -> dict[str, str]:
    lock = root / str(manifest["dependency_lock"])
    digest_file = root / str(manifest["dependency_lock_digest"])
    expected, name = digest_file.read_text(encoding="utf-8").strip().split(maxsplit=1)
    if name.lstrip("*") != "uv.lock":
        raise AssertionError(f"malformed lock digest name for {manifest['product']}")
    actual = _sha256(lock)
    if actual != expected:
        raise AssertionError(f"lock digest mismatch for {manifest['product']}")
    return {"sha256": actual, "status": "pass"}


def evaluate(roots: list[Path]) -> dict[str, object]:
    products: list[dict[str, object]] = []
    protocol_hashes: set[str] = set()
    observability_hashes: set[str] = set()
    seen_products: set[str] = set()
    seen_branches: set[str] = set()
    seen_surfaces: set[str] = set()

    for root in roots:
        manifest = json.loads(
            (root / "docs" / "energy_aware_product_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        product = str(manifest["product"])
        branch = str(manifest["canonical_branch"])
        surface = str(manifest["public_surface"])
        if product in seen_products or branch in seen_branches or surface in seen_surfaces:
            raise AssertionError(
                "portfolio products, canonical branches and public surfaces must be unique"
            )
        seen_products.add(product)
        seen_branches.add(branch)
        seen_surfaces.add(surface)

        contracts = {script: _run_contract(root, script) for script in CONTRACT_SCRIPTS}
        lock = _verify_lock(root, manifest)
        protocol_hashes.add(_sha256(root / "docs" / "ENERGY_AWARE_PROTOCOL_V1.md"))
        observability_hashes.add(_sha256(root / "app" / "energy_aware_observability.py"))
        products.append(
            {
                "product": product,
                "canonical_branch": branch,
                "public_surface": surface,
                "protocol_version": manifest["protocol_version"],
                "contracts": contracts,
                "dependency_lock": lock,
                "reason_code_count": len(manifest["reason_codes"]),
                "active_stage_count": len(manifest["stages_active"]),
            }
        )

    protocol_versions = {str(item["protocol_version"]) for item in products}
    if protocol_versions != {"energy-aware.protocol.v1"}:
        raise AssertionError(
            f"portfolio protocol versions diverged: {sorted(protocol_versions)}"
        )
    if len(protocol_hashes) != 1:
        raise AssertionError("ENERGY_AWARE_PROTOCOL_V1.md diverged across canonical products")
    if len(observability_hashes) != 1:
        raise AssertionError("neutral operational event implementation diverged across products")
    if seen_products != {"estimator", "eachat", "eacode"}:
        raise AssertionError(f"unexpected canonical product set: {sorted(seen_products)}")

    check_count = len(products) * (len(CONTRACT_SCRIPTS) + 1) + 3
    return {
        "suite_version": "energy-aware.portfolio-eval.v1",
        "protocol_version": "energy-aware.protocol.v1",
        "products": products,
        "cross_product_checks": {
            "canonical_product_set": "pass",
            "protocol_document_identical": "pass",
            "observability_contract_identical": "pass",
        },
        "check_count": check_count,
        "failed_checks": 0,
        "status": "pass",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", nargs=3, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate([path.resolve() for path in args.roots])
    encoded = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
