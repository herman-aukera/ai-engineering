"""Milestone 20-21: release audit and deployment readiness checks."""

from __future__ import annotations

from app.energy_chat.release_audit import (
    build_release_audit,
    check_deployment_readiness,
)


def test_release_audit_includes_all_claim_boundaries() -> None:
    audit = build_release_audit("EACHAT", "abc123def456")
    assert len(audit.claims) >= 5
    assert audit.branch == "EACHAT"
    assert audit.commit_sha == "abc123def456"


def test_allowed_claims_have_current_evidence() -> None:
    audit = build_release_audit("EACHAT", "sha")
    for claim in audit.claims:
        if claim.status == "allowed":
            assert claim.current_evidence, f"{claim.claim_id} has no evidence"


def test_blocked_claims_have_required_evidence_listed() -> None:
    audit = build_release_audit("EACHAT", "sha")
    for claim in audit.claims:
        if claim.status == "blocked_missing_evidence":
            assert claim.required_evidence, (
                f"{claim.claim_id} must list required evidence"
            )


def test_kimi_best_claim_is_blocked() -> None:
    audit = build_release_audit("EACHAT", "sha")
    kimi_claim = next(c for c in audit.claims if "kimi" in c.claim_id.lower())
    assert kimi_claim.status == "blocked_missing_evidence"


def test_auto_routing_claim_is_blocked() -> None:
    audit = build_release_audit("EACHAT", "sha")
    auto_claim = next(c for c in audit.claims if "auto_routing" in c.claim_id)
    assert auto_claim.status == "blocked_missing_evidence"


def test_production_ready_is_blocked() -> None:
    audit = build_release_audit("EACHAT", "sha")
    prod_claim = next(c for c in audit.claims if c.claim_id == "production_ready")
    assert prod_claim.status == "blocked_missing_evidence"


def test_deployment_readiness_all_false_by_default() -> None:
    result = check_deployment_readiness()
    assert result["ready"] is False


def test_deployment_readiness_true_when_all_gates_green() -> None:
    result = check_deployment_readiness(
        ci_green=True,
        deterministic_tests_passing=True,
        secrets_scan_clean=True,
        docker_config_exists=True,
    )
    assert result["ready"] is True
