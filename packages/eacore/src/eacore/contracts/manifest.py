from __future__ import annotations

from pydantic import Field

from .base import StrictModel


class ArtifactManifestEntry(StrictModel):
    artifact_id: str
    relative_path: str
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class ArtifactManifest(StrictModel):
    manifest_id: str
    root_ref: str
    entries: tuple[ArtifactManifestEntry, ...]
