"""Validate one product against Energy-Aware Protocol V1 without product coupling."""

from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
MANIFEST_PATH = PROJECT_ROOT / "docs" / "energy_aware_product_manifest.json"
PROTOCOL_PATH = PROJECT_ROOT / "docs" / "ENERGY_AWARE_PROTOCOL_V1.md"

STAGES = {
    "INGEST", "UNDERSTAND", "GATHER_EVIDENCE", "PROPOSE", "CRITIQUE", "SCORE",
    "DECIDE", "REPAIR", "AUTHORIZE", "EXECUTE", "VERIFY", "RECORD",
}
REASON_CODE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
REQUIRED_INVARIANTS = {
    "deterministic_hard_constraints",
    "deterministic_budget_authority",
    "planned_served_distinct",
    "repair_creates_reevaluated_revision",
    "signed_human_authority",
    "replay_safe",
    "durable_authoritative_state",
    "secrets_excluded_from_evidence",
    "hidden_reasoning_excluded",
}


def _load_manifest() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _resolve_declared_path(value: object) -> Path:
    if not isinstance(value, str) or not value:
        raise AssertionError(f"invalid manifest path: {value!r}")
    project_path = PROJECT_ROOT / value
    if project_path.is_file():
        return project_path
    repo_path = REPO_ROOT / value
    if repo_path.is_file():
        return repo_path
    raise AssertionError(f"manifest path is missing: {value}")


def verify() -> dict[str, object]:
    manifest = _load_manifest()
    protocol = PROTOCOL_PATH.read_text(encoding="utf-8")
    version = manifest.get("protocol_version")
    if version != "energy-aware.protocol.v1" or str(version) not in protocol:
        raise AssertionError("product manifest and protocol document version diverge")

    active = set(manifest.get("stages_active", []))
    omitted = set(manifest.get("stages_not_applicable", []))
    if active & omitted:
        raise AssertionError("Energy-Aware stages cannot be both active and N/A")
    if active | omitted != STAGES:
        raise AssertionError(
            f"Energy-Aware stages are not fully accounted for: {sorted(STAGES - active - omitted)}"
        )

    invariants = manifest.get("required_invariants")
    if not isinstance(invariants, dict):
        raise AssertionError("required_invariants must be an object")
    missing = sorted(REQUIRED_INVARIANTS - set(invariants))
    false_values = sorted(
        name for name in REQUIRED_INVARIANTS if invariants.get(name) is not True
    )
    if missing or false_values:
        raise AssertionError(
            f"required authority invariants are not proven: missing={missing}, false={false_values}"
        )

    reason_codes = manifest.get("reason_codes")
    if not isinstance(reason_codes, list) or not reason_codes:
        raise AssertionError("reason_codes must be a non-empty list")
    invalid_codes = sorted(
        code
        for code in reason_codes
        if not isinstance(code, str) or not REASON_CODE.fullmatch(code)
    )
    if invalid_codes:
        raise AssertionError(f"invalid stable reason codes: {invalid_codes}")

    for key in (
        "production_entrypoint",
        "public_surface_owner",
        "dependency_lock",
        "dependency_lock_digest",
    ):
        _resolve_declared_path(manifest.get(key))

    surface = manifest.get("public_surface")
    major = manifest.get("public_api_major")
    if not isinstance(surface, str) or not isinstance(major, str) or f"/{major}/" not in surface:
        raise AssertionError("canonical public surface must carry an explicit API major")

    composition_source = _resolve_declared_path(manifest.get("production_entrypoint")).read_text(
        encoding="utf-8"
    )
    route_source = _resolve_declared_path(manifest.get("public_surface_owner")).read_text(
        encoding="utf-8"
    )
    markers = manifest.get("public_surface_markers")
    if not isinstance(markers, list) or not markers:
        raise AssertionError("public_surface_markers must be a non-empty list")
    combined_route_source = composition_source + "\n" + route_source
    missing_markers = [
        marker
        for marker in markers
        if not isinstance(marker, str) or marker not in combined_route_source
    ]
    if missing_markers:
        raise AssertionError(f"canonical route composition markers are missing: {missing_markers}")

    evidence = manifest.get("resilience_evidence")
    if not isinstance(evidence, list) or not evidence:
        raise AssertionError("resilience_evidence must identify executable evidence")
    missing_evidence: list[str] = []
    for path in evidence:
        try:
            _resolve_declared_path(path)
        except AssertionError:
            missing_evidence.append(str(path))
    if missing_evidence:
        raise AssertionError(f"declared resilience evidence is missing: {missing_evidence}")

    return {
        "schema_version": manifest["schema_version"],
        "protocol_version": version,
        "product": manifest["product"],
        "canonical_branch": manifest["canonical_branch"],
        "active_stage_count": len(active),
        "not_applicable_stage_count": len(omitted),
        "invariant_count": len(REQUIRED_INVARIANTS),
        "reason_code_count": len(reason_codes),
        "status": "pass",
    }


def main() -> None:
    print(json.dumps(verify(), sort_keys=True))


if __name__ == "__main__":
    main()
