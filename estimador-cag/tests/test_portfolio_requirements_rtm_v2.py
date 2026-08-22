from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.verify_portfolio_requirements import load_rtm, validate_rtm


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _row(requirement_id: str) -> dict[str, object]:
    return {
        "requirement_id": requirement_id,
        "requirement": "test requirement",
        "source_family": "test",
        "product": "portfolio",
        "applicability": "REPOSITORY_CONTROLLED",
        "implementation": "bundle:supply_chain",
        "test": "bundle:supply_chain",
        "CI_evidence": "bundle:supply_chain",
        "status": "PASS",
        "external_reason_if_any": None,
        "repository_controlled": True,
    }


def _base() -> dict[str, object]:
    return {
        "schema_version": "energy-aware.portfolio-rtm.v1",
        "evidence_bundles": {
            "supply_chain": {
                "implementation": ["main:impl.py"],
                "test": ["main:test_impl.py"],
                "CI_evidence": ["main:.github/workflows/ci.yml#gate"],
            }
        },
        "requirements": [_row("SC-001")],
    }


def test_v2_overlay_appends_unique_evidence_and_requirements(tmp_path: Path) -> None:
    base_path = tmp_path / "base.json"
    wrapper_path = tmp_path / "v2.json"
    _write(base_path, _base())
    _write(
        wrapper_path,
        {
            "schema_version": "energy-aware.portfolio-rtm.v2",
            "base_rtm": "base.json",
            "evidence_bundle_additions": {
                "supply_chain": {
                    "implementation": ["main:tool.py", "main:impl.py"],
                    "test": ["main:test_tool.py"],
                    "CI_evidence": [],
                }
            },
            "requirements": [_row("SC-006")],
        },
    )

    payload = load_rtm(wrapper_path)
    bundle = payload["evidence_bundles"]["supply_chain"]
    assert bundle["implementation"] == ["main:impl.py", "main:tool.py"]
    assert bundle["test"] == ["main:test_impl.py", "main:test_tool.py"]
    assert [row["requirement_id"] for row in payload["requirements"]] == ["SC-001", "SC-006"]
    assert validate_rtm(payload) == []


def test_v2_overlay_rejects_parent_path_escape(tmp_path: Path) -> None:
    wrapper_path = tmp_path / "v2.json"
    _write(
        wrapper_path,
        {
            "schema_version": "energy-aware.portfolio-rtm.v2",
            "base_rtm": "../base.json",
            "evidence_bundle_additions": {},
            "requirements": [_row("SC-006")],
        },
    )

    with pytest.raises(ValueError, match="inside the RTM directory"):
        load_rtm(wrapper_path)


def test_v2_overlay_duplicate_requirement_is_rejected_by_validator(tmp_path: Path) -> None:
    base_path = tmp_path / "base.json"
    wrapper_path = tmp_path / "v2.json"
    _write(base_path, _base())
    _write(
        wrapper_path,
        {
            "schema_version": "energy-aware.portfolio-rtm.v2",
            "base_rtm": "base.json",
            "evidence_bundle_additions": {},
            "requirements": [_row("SC-001")],
        },
    )

    errors = validate_rtm(load_rtm(wrapper_path))
    assert any("duplicate requirement_id: SC-001" in error for error in errors)
