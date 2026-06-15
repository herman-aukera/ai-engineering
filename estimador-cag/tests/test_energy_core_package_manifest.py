from pathlib import Path

from energy_core.package_manifest import (
    build_package_manifest,
    format_package_manifest_markdown,
    format_package_manifest_text,
)


def test_package_manifest_is_complete_from_project_root() -> None:
    manifest = build_package_manifest(Path("."))

    assert manifest["complete"] is True
    assert manifest["present_total"] == manifest["required_total"]
    assert manifest["missing_required"] == []
    assert "energy_core/" in manifest["copy_roots"]
    assert ".energy/" in manifest["copy_roots"]


def test_package_manifest_includes_latest_review_and_export_surfaces() -> None:
    manifest = build_package_manifest(Path("."))
    paths = {item["relative_path"] for item in manifest["files"]}

    assert "energy_core/review_pack.py" in paths
    assert "energy_core/review_pack_cli.py" in paths
    assert "energy_core/scaffold.py" in paths
    assert "energy_core/scaffold_cli.py" in paths
    assert "energy_core/export_plan.py" in paths
    assert "energy_core/export_plan_cli.py" in paths
    assert "energy_core/critic_coverage.py" in paths
    assert "energy_core/critic_coverage_cli.py" in paths
    assert "energy_core/policy_roadmap.py" in paths
    assert "energy_core/policy_roadmap_cli.py" in paths
    assert "energy_core/ledger_integrity.py" in paths
    assert "energy_core/ledger_integrity_cli.py" in paths
    assert "energy_core/candidate_readiness.py" in paths
    assert "energy_core/candidate_readiness_cli.py" in paths
    assert "energy_core/surface_consistency.py" in paths
    assert "energy_core/surface_consistency_cli.py" in paths
    assert "energy_core/nightly_status.py" in paths
    assert "energy_core/nightly_status_cli.py" in paths
    assert "scripts/energy_core_review_pack_smoke.py" in paths
    assert "scripts/energy_core_scaffold_smoke.py" in paths
    assert "scripts/energy_core_export_plan_smoke.py" in paths
    assert "scripts/energy_core_critic_coverage_smoke.py" in paths
    assert "scripts/energy_core_policy_roadmap_smoke.py" in paths
    assert "scripts/energy_core_ledger_integrity_smoke.py" in paths
    assert "scripts/energy_core_candidate_readiness_smoke.py" in paths
    assert "scripts/energy_core_surface_consistency_smoke.py" in paths
    assert "scripts/energy_core_nightly_status_v3_smoke.py" in paths
    assert "scripts/energy_core_full_gate.py" in paths
    assert "docs/energy_aware_code_review_pack.md" in paths
    assert "docs/energy_aware_code_critic_coverage.md" in paths
    assert "docs/energy_aware_code_policy_roadmap.md" in paths
    assert "docs/energy_aware_code_ledger_integrity.md" in paths
    assert "docs/energy_aware_code_nightly_status.md" in paths


def test_package_manifest_resolves_repository_root() -> None:
    manifest = build_package_manifest(Path(".."))

    assert manifest["complete"] is True
    assert manifest["project_root"].endswith("estimador-cag")


def test_package_manifest_reports_missing_files(tmp_path: Path) -> None:
    manifest = build_package_manifest(tmp_path)

    assert manifest["complete"] is False
    assert "energy_core/models.py" in manifest["missing_required"]


def test_package_manifest_formats_text_and_markdown() -> None:
    manifest = build_package_manifest(Path("."))

    text = format_package_manifest_text(manifest)
    markdown = format_package_manifest_markdown(manifest)

    assert "Energy Aware Code Package Manifest" in text
    assert "Complete: True" in text
    assert "# Energy Aware Code Package Manifest" in markdown
    assert "## Copy roots" in markdown
