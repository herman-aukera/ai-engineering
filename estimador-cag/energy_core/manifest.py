from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from energy_core.hashing import sha256_file

MANIFEST_VERSION = "1.0.0"


def build_manifest(
    paths: list[str | Path],
    *,
    root: str | Path,
    generated_at: str,
) -> dict[str, Any]:
    """Describe exact file bytes relative to a bounded manifest root."""

    root_path = Path(root).resolve()
    entries = []
    for value in sorted((Path(path).resolve() for path in paths), key=str):
        if not value.is_relative_to(root_path):
            raise ValueError(f"File is outside manifest root: {value}")
        relative = value.relative_to(root_path).as_posix()
        entries.append(
            {
                "path": relative,
                "size_bytes": value.stat().st_size,
                "sha256": sha256_file(value),
            }
        )
    return {
        "manifest_version": MANIFEST_VERSION,
        "generated_at": generated_at,
        "hash_algorithm": "sha256",
        "authenticity": "requires-trusted-manifest-copy",
        "entries": entries,
    }


def write_manifest(path: str | Path, manifest: dict[str, Any]) -> Path:
    """Create a manifest without replacing an existing trusted copy."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return destination


def verify_manifest(path: str | Path, *, root: str | Path) -> dict[str, Any]:
    """Compare current bytes with a manifest supplied through a trusted channel."""

    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    root_path = Path(root).resolve()
    missing: list[str] = []
    mismatched: list[dict[str, Any]] = []
    invalid_paths: list[str] = []
    verified: list[str] = []
    for entry in payload.get("entries", []):
        relative = entry.get("path")
        if not isinstance(relative, str):
            invalid_paths.append(str(relative))
            continue
        candidate = (root_path / relative).resolve()
        if not candidate.is_relative_to(root_path):
            invalid_paths.append(relative)
            continue
        if not candidate.is_file():
            missing.append(relative)
            continue
        actual_hash = sha256_file(candidate)
        actual_size = candidate.stat().st_size
        if actual_hash != entry.get("sha256") or actual_size != entry.get("size_bytes"):
            mismatched.append(
                {
                    "path": relative,
                    "expected_sha256": entry.get("sha256"),
                    "actual_sha256": actual_hash,
                    "expected_size_bytes": entry.get("size_bytes"),
                    "actual_size_bytes": actual_size,
                }
            )
        else:
            verified.append(relative)
    return {
        "manifest_path": str(manifest_path.resolve()),
        "manifest_version": payload.get("manifest_version"),
        "authenticity": payload.get("authenticity"),
        "complete": not (missing or mismatched or invalid_paths),
        "verified": verified,
        "missing": missing,
        "mismatched": mismatched,
        "invalid_paths": invalid_paths,
    }
