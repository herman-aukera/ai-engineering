from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

VALID_STATUSES = {"PASS", "N/A", "BLOCKED_EXTERNAL"}
APPROVED_EXTERNAL = {
    "LOCAL_MANUAL_TEST",
    "TEMPORARY_PUBLIC_STAGING",
    "AWS_SPOT_RDS",
    "LIVE_PROVIDER",
    "REAL_OIDC",
    "GITHUB_ADMINISTRATION",
    "REPOSITORY_EXTRACTION",
    "REAL_TRAFFIC_SLO",
}
REQUIRED_FIELDS = {
    "requirement_id",
    "requirement",
    "source_family",
    "product",
    "applicability",
    "implementation",
    "test",
    "CI_evidence",
    "status",
    "external_reason_if_any",
    "repository_controlled",
}
BUNDLE_FIELDS = ("implementation", "test", "CI_evidence")
V1_SCHEMA = "energy-aware.portfolio-rtm.v1"
V2_SCHEMA = "energy-aware.portfolio-rtm.v2"


def _parse_repos(values: list[str]) -> dict[str, Path]:
    repos: dict[str, Path] = {}
    for value in values:
        branch, separator, raw_path = value.partition("=")
        if not separator or not branch or not raw_path:
            raise ValueError(f"invalid --repo value: {value!r}; expected BRANCH=PATH")
        repos[branch] = Path(raw_path)
    return repos


def _resolve_bundle_ref(value: object, bundles: dict[str, object], field: str) -> list[str]:
    if not isinstance(value, str) or not value.startswith("bundle:"):
        return []
    bundle_name = value.split(":", 1)[1]
    bundle = bundles.get(bundle_name)
    if not isinstance(bundle, dict):
        return []
    entries = bundle.get(field)
    if not isinstance(entries, list) or not entries or not all(isinstance(item, str) and item for item in entries):
        return []
    return entries


def _validate_paths(entries: list[str], repos: dict[str, Path], requirement_id: str, field: str) -> list[str]:
    errors: list[str] = []
    if not repos:
        return errors
    for entry in entries:
        locator = entry.split("#", 1)[0]
        branch, separator, relative = locator.partition(":")
        if not separator:
            continue
        repo = repos.get(branch)
        if repo is None:
            errors.append(f"{requirement_id}: {field} references unknown branch {branch}")
            continue
        if not (repo / relative).exists():
            errors.append(f"{requirement_id}: {field} evidence path missing: {entry}")
    return errors


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: RTM root must be an object")
    return payload


def _resolve_local_base(wrapper_path: Path, raw_base: object) -> Path:
    if not isinstance(raw_base, str) or not raw_base:
        raise ValueError(f"{wrapper_path}: v2 base_rtm must be a non-empty relative path")
    base = Path(raw_base)
    if base.is_absolute() or ".." in base.parts:
        raise ValueError(f"{wrapper_path}: v2 base_rtm must stay inside the RTM directory")
    resolved = (wrapper_path.parent / base).resolve()
    if resolved.parent != wrapper_path.parent.resolve():
        raise ValueError(f"{wrapper_path}: v2 base_rtm must be a sibling file")
    return resolved


def load_rtm(path: Path) -> dict[str, object]:
    """Load a v1 RTM or compose an append-only v2 wrapper over a sibling v1 RTM."""
    payload = _load_json(path)
    schema = payload.get("schema_version")
    if schema == V1_SCHEMA:
        return payload
    if schema != V2_SCHEMA:
        return payload

    base_path = _resolve_local_base(path, payload.get("base_rtm"))
    base = _load_json(base_path)
    if base.get("schema_version") != V1_SCHEMA:
        raise ValueError(f"{path}: v2 base_rtm must reference a {V1_SCHEMA} document")

    composed = copy.deepcopy(base)
    bundles = composed.get("evidence_bundles")
    requirements = composed.get("requirements")
    if not isinstance(bundles, dict) or not isinstance(requirements, list):
        raise ValueError(f"{path}: base RTM is structurally invalid")

    additions = payload.get("evidence_bundle_additions", {})
    if not isinstance(additions, dict):
        raise ValueError(f"{path}: evidence_bundle_additions must be an object")
    for bundle_name, addition in additions.items():
        target = bundles.get(bundle_name)
        if not isinstance(target, dict):
            raise ValueError(f"{path}: unknown evidence bundle {bundle_name!r}")
        if not isinstance(addition, dict):
            raise ValueError(f"{path}: evidence addition for {bundle_name!r} must be an object")
        unknown_fields = set(addition) - set(BUNDLE_FIELDS)
        if unknown_fields:
            raise ValueError(
                f"{path}: evidence addition for {bundle_name!r} has unknown fields {sorted(unknown_fields)}"
            )
        for field in BUNDLE_FIELDS:
            extra = addition.get(field, [])
            if not isinstance(extra, list) or not all(isinstance(item, str) and item for item in extra):
                raise ValueError(f"{path}: {bundle_name}.{field} additions must be non-empty strings")
            existing = target.get(field)
            if not isinstance(existing, list):
                raise ValueError(f"{path}: base bundle {bundle_name}.{field} is not a list")
            for item in extra:
                if item not in existing:
                    existing.append(item)

    extra_requirements = payload.get("requirements")
    if not isinstance(extra_requirements, list) or not extra_requirements:
        raise ValueError(f"{path}: v2 requirements must be a non-empty list")
    requirements.extend(copy.deepcopy(extra_requirements))
    return composed


def validate_rtm(payload: dict[str, object], repos: dict[str, Path] | None = None) -> list[str]:
    repos = repos or {}
    errors: list[str] = []
    bundles = payload.get("evidence_bundles")
    requirements = payload.get("requirements")
    if payload.get("schema_version") != V1_SCHEMA:
        errors.append(f"schema_version must be {V1_SCHEMA}")
    if not isinstance(bundles, dict):
        return errors + ["evidence_bundles must be an object"]
    if not isinstance(requirements, list) or not requirements:
        return errors + ["requirements must be a non-empty list"]

    seen: set[str] = set()
    for index, row in enumerate(requirements):
        if not isinstance(row, dict):
            errors.append(f"row {index}: requirement must be an object")
            continue
        missing = REQUIRED_FIELDS - row.keys()
        if missing:
            errors.append(f"row {index}: missing fields {sorted(missing)}")
            continue
        requirement_id = str(row["requirement_id"])
        if requirement_id in seen:
            errors.append(f"duplicate requirement_id: {requirement_id}")
        seen.add(requirement_id)
        status = row["status"]
        if status not in VALID_STATUSES:
            errors.append(f"{requirement_id}: invalid status {status!r}")
            continue
        repository_controlled = row["repository_controlled"] is True
        if repository_controlled and status != "PASS":
            errors.append(f"{requirement_id}: repository-controlled requirement must PASS, got {status}")
        if status == "PASS":
            for field in BUNDLE_FIELDS:
                entries = _resolve_bundle_ref(row[field], bundles, field)
                if not entries:
                    errors.append(f"{requirement_id}: PASS row lacks resolvable {field} evidence")
                    continue
                errors.extend(_validate_paths(entries, repos, requirement_id, field))
            if row["external_reason_if_any"] not in (None, ""):
                errors.append(f"{requirement_id}: PASS row must not carry external blocker")
        elif status == "BLOCKED_EXTERNAL":
            reason = row["external_reason_if_any"]
            if repository_controlled:
                errors.append(f"{requirement_id}: repository-controlled row cannot be BLOCKED_EXTERNAL")
            if reason not in APPROVED_EXTERNAL:
                errors.append(f"{requirement_id}: unapproved external blocker {reason!r}")
        elif status == "N/A" and repository_controlled:
            errors.append(f"{requirement_id}: repository-controlled requirement cannot be N/A")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rtm",
        default=str(Path(__file__).resolve().parents[2] / "docs" / "portfolio_requirements_traceability_v2.json"),
    )
    parser.add_argument("--repo", action="append", default=[])
    args = parser.parse_args()
    try:
        payload = load_rtm(Path(args.rtm))
        repos = _parse_repos(args.repo)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc))
        return 2
    errors = validate_rtm(payload, repos)
    if errors:
        print("\n".join(errors))
        return 1
    rows = payload["requirements"]
    counts = {status: sum(1 for row in rows if row["status"] == status) for status in VALID_STATUSES}
    print(
        "PORTFOLIO_RTM_OK "
        f"total={len(rows)} pass={counts['PASS']} na={counts['N/A']} "
        f"blocked_external={counts['BLOCKED_EXTERNAL']} fail=0"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
