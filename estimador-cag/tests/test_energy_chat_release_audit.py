"""Evidence-driven release and production-readiness gates."""

from __future__ import annotations

from app.energy_chat.release_audit import (
    ReleaseEvidence,
    build_release_audit,
    check_deployment_readiness,
)


def _current_ci_evidence() -> ReleaseEvidence:
    return ReleaseEvidence(
        exact_head_ci_green=True,
        deterministic_tests_passing=True,
        process_local_replay_proven=True,
        human_resume_proven=True,
        postgres_restart_proven=True,
        postgres_redaction_retention_proven=True,
        browser_contract_tests_passing=True,
    )


def test_release_audit_includes_all_claim_boundaries() -> None:
    audit = build_release_audit("EACHAT", "abc123def456")
    assert len(audit.claims) >= 8
    assert audit.branch == "EACHAT"
    assert audit.commit_sha == "abc123def456"


def test_allowed_claims_have_supplied_current_evidence() -> None:
    audit = build_release_audit("EACHAT", "sha", evidence=_current_ci_evidence())
    for claim in audit.claims:
        if claim.status == "allowed":
            assert claim.current_evidence, f"{claim.claim_id} has no evidence"


def test_blocked_claims_list_the_missing_evidence() -> None:
    audit = build_release_audit("EACHAT", "sha", evidence=_current_ci_evidence())
    for claim in audit.claims:
        if claim.status == "blocked_missing_evidence":
            assert claim.required_evidence, (
                f"{claim.claim_id} must list required evidence"
            )


def test_current_ci_evidence_allows_proven_foundations_only() -> None:
    audit = build_release_audit("EACHAT", "sha", evidence=_current_ci_evidence())
    claims = {claim.claim_id: claim for claim in audit.claims}

    assert claims["graph_backed_api"].status == "allowed"
    assert claims["checkpoint_replay"].status == "allowed"
    assert claims["human_gates"].status == "allowed"
    assert claims["postgresql_persistence"].status == "allowed"
    assert claims["browser_product_contract"].status == "allowed"
    assert claims["context_compaction_runtime"].status == "blocked_missing_evidence"
    assert claims["multi_agent_runtime"].status == "blocked_missing_evidence"
    assert claims["production_ready"].status == "blocked_missing_evidence"


def test_m18_contracts_are_not_counted_as_runtime_evidence() -> None:
    audit = build_release_audit("EACHAT", "sha", evidence=_current_ci_evidence())
    claims = {claim.claim_id: claim for claim in audit.claims}

    assert "contract" in claims["context_compaction_runtime"].notes.lower()
    assert "contract" in claims["multi_agent_runtime"].notes.lower()


def test_kimi_best_and_auto_routing_claims_remain_blocked() -> None:
    audit = build_release_audit("EACHAT", "sha", evidence=_current_ci_evidence())
    claims = {claim.claim_id: claim for claim in audit.claims}

    assert claims["kimi_k3_best"].status == "blocked_missing_evidence"
    assert claims["auto_routing_superior"].status == "blocked_missing_evidence"


def test_deployment_readiness_all_false_by_default() -> None:
    result = check_deployment_readiness()
    assert result["ready"] is False


def test_unit_and_ci_gates_are_not_enough_for_production() -> None:
    result = check_deployment_readiness(
        exact_head_ci_green=True,
        deterministic_tests_passing=True,
        secrets_scan_clean=True,
        docker_config_exists=True,
        postgres_restart_proven=True,
    )
    assert result["ready"] is False
    assert result["browser_smoke_proven"] is False
    assert result["live_provider_smoke_proven"] is False


def test_deployment_readiness_requires_every_production_gate() -> None:
    result = check_deployment_readiness(
        exact_head_ci_green=True,
        deterministic_tests_passing=True,
        secrets_scan_clean=True,
        docker_config_exists=True,
        postgres_restart_proven=True,
        browser_smoke_proven=True,
        live_provider_smoke_proven=True,
        security_review_complete=True,
        deployment_health_proven=True,
    )
    assert result["ready"] is True
