from __future__ import annotations

from pathlib import Path

from eacore.contracts import ArtifactManifest, ArtifactManifestEntry, ManifestPathError

from .hashing import sha256_hex


def build_manifest(*, root: Path, manifest_id: str, relative_paths: list[str]) -> ArtifactManifest:
    resolved_root = root.resolve()
    entries: list[ArtifactManifestEntry] = []
    for relative in sorted(set(relative_paths)):
        candidate = (resolved_root / relative).resolve()
        try:
            candidate.relative_to(resolved_root)
        except ValueError as exc:
            raise ManifestPathError(f"path escapes manifest root: {relative}") from exc
        if not candidate.is_file():
            raise ManifestPathError(f"manifest path is not a file: {relative}")
        payload = candidate.read_bytes()
        entries.append(
            ArtifactManifestEntry(
                artifact_id=f"artifact:{relative}",
                relative_path=relative,
                content_hash=sha256_hex(payload),
                size_bytes=len(payload),
            )
        )
    return ArtifactManifest(
        manifest_id=manifest_id,
        root_ref=str(resolved_root),
        entries=tuple(entries),
    )
