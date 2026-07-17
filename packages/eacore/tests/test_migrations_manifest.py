from pathlib import Path

import pytest

from eacore.contracts import ManifestPathError
from eacore.engine import MigrationRegistry, build_manifest


def test_migration_does_not_mutate_input() -> None:
    registry = MigrationRegistry()
    registry.register("thing", "1.0.0", "1.1.0", lambda value: {**value, "added": True})
    source = {"name": "x"}
    result = registry.migrate("thing", "1.0.0", "1.1.0", source)
    assert source == {"name": "x"}
    assert result == {"name": "x", "added": True}


def test_mutating_migration_receives_a_copy() -> None:
    registry = MigrationRegistry()

    def mutate_copy(value):
        value["changed"] = True
        return value

    registry.register("thing", "1.0.0", "1.1.0", mutate_copy)
    source = {"name": "x"}
    result = registry.migrate("thing", "1.0.0", "1.1.0", source)
    assert source == {"name": "x"}
    assert result == {"name": "x", "changed": True}


def test_manifest_is_bounded(tmp_path: Path) -> None:
    (tmp_path / "artifact.txt").write_text("safe", encoding="utf-8")
    manifest = build_manifest(
        root=tmp_path, manifest_id="manifest:1", relative_paths=["artifact.txt"]
    )
    assert manifest.entries[0].relative_path == "artifact.txt"
    assert manifest.entries[0].size_bytes == 4


def test_manifest_rejects_path_traversal(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("unsafe", encoding="utf-8")
    with pytest.raises(ManifestPathError):
        build_manifest(root=tmp_path, manifest_id="manifest:1", relative_paths=["../outside.txt"])
