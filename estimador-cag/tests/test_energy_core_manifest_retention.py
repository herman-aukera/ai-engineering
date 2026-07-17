from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from energy_core.evidence_recovery import recover_evidence_ledger
from energy_core.manifest import build_manifest, verify_manifest, write_manifest
from energy_core.manifest_cli import main as manifest_main
from energy_core.models import EvidenceRecord
from energy_core.retention import build_retention_report


def test_manifest_verifies_exact_files_and_detects_tampering(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.jsonl"
    decisions = tmp_path / "decisions.jsonl"
    manifest_path = tmp_path / "manifest.json"
    evidence.write_text('{"evidence_id":"ev-1"}\n', encoding="utf-8")
    decisions.write_text("", encoding="utf-8")
    manifest = build_manifest(
        [evidence, decisions],
        root=tmp_path,
        generated_at="2026-07-17T12:00:00Z",
    )

    write_manifest(manifest_path, manifest)
    clean = verify_manifest(manifest_path, root=tmp_path)
    evidence.write_text("tampered\n", encoding="utf-8")
    tampered = verify_manifest(manifest_path, root=tmp_path)

    assert clean["complete"] is True
    assert clean["mismatched"] == []
    assert tampered["complete"] is False
    assert tampered["mismatched"][0]["path"] == "evidence.jsonl"
    assert manifest["authenticity"] == "requires-trusted-manifest-copy"


def test_manifest_rejects_paths_outside_root_and_overwrite(tmp_path: Path) -> None:
    inside = tmp_path / "inside.txt"
    outside = tmp_path.parent / "outside.txt"
    inside.write_text("inside", encoding="utf-8")
    outside.write_text("outside", encoding="utf-8")
    try:
        build_manifest([outside], root=tmp_path, generated_at="2026-07-17T12:00:00Z")
    except ValueError as exc:
        assert "outside manifest root" in str(exc)
    else:
        raise AssertionError("manifest must reject paths outside its root")

    manifest_path = tmp_path / "manifest.json"
    manifest = build_manifest([inside], root=tmp_path, generated_at="2026-07-17T12:00:00Z")
    write_manifest(manifest_path, manifest)
    try:
        write_manifest(manifest_path, manifest)
    except FileExistsError:
        pass
    else:
        raise AssertionError("trusted manifest write must be create-only")


def test_retention_report_marks_expired_records_for_review_without_deleting() -> None:
    records = [
        EvidenceRecord(
            evidence_id="ev-old-transient",
            run_id="run-1",
            recorded_at="2025-01-01T00:00:00Z",
            type="agent_explanation",
            status="pass",
            summary="old transient evidence",
        ),
        EvidenceRecord(
            evidence_id="ev-no-time",
            type="git_diff",
            status="pass",
            summary="legacy evidence",
        ),
    ]

    report = build_retention_report(
        records,
        now=datetime(2026, 7, 17, tzinfo=UTC),
    )

    assert report["deleted_record_total"] == 0
    assert report["eligible_for_review"] == ["ev-old-transient"]
    assert report["retained_missing_timestamp"] == ["ev-no-time"]
    assert report["policy"]["transient_days"] == 30


def test_evidence_recovery_preserves_source_and_quarantines_invalid(tmp_path: Path) -> None:
    source = tmp_path / "evidence.jsonl"
    recovered = tmp_path / "recovered.jsonl"
    quarantine = tmp_path / "quarantine.jsonl"
    valid = {
        "evidence_id": "ev-1",
        "type": "pytest_output",
        "status": "pass",
        "summary": "ok",
    }
    original = json.dumps(valid) + "\n{broken\n"
    source.write_text(original, encoding="utf-8")

    report = recover_evidence_ledger(source, recovered, quarantine)

    assert source.read_text(encoding="utf-8") == original
    assert report["recovered_record_total"] == 1
    assert report["quarantined_record_total"] == 1
    loaded = json.loads(recovered.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == "1.0.0"
    assert loaded["evidence_id"] == "ev-1"


def test_manifest_cli_fails_after_tampering(tmp_path: Path, capsys) -> None:
    artifact = tmp_path / "artifact.txt"
    manifest = tmp_path / "manifest.json"
    artifact.write_text("original", encoding="utf-8")
    assert manifest_main(
        [
            "generate",
            "--root",
            str(tmp_path),
            "--output",
            str(manifest),
            str(artifact),
        ]
    ) == 0
    capsys.readouterr()
    artifact.write_text("changed", encoding="utf-8")

    result = manifest_main(
        [
            "verify",
            "--root",
            str(tmp_path),
            "--manifest",
            str(manifest),
            "--fail-on-mismatch",
        ]
    )
    report = json.loads(capsys.readouterr().out)

    assert result == 1
    assert report["complete"] is False


def test_committed_mixed_evidence_fixture_recovery(tmp_path: Path) -> None:
    source = Path(
        ".energy/specs/0004-retention-trusted-manifest/fixtures/mixed_evidence.jsonl"
    )
    before = source.read_bytes()

    report = recover_evidence_ledger(
        source,
        tmp_path / "recovered.jsonl",
        tmp_path / "quarantine.jsonl",
    )

    assert source.read_bytes() == before
    assert report["source_record_total"] == 2
    assert report["recovered_record_total"] == 1
    assert report["quarantined_record_total"] == 1
