"""Milestone 15: evidence body hashing, verification, freshness, and citation validation."""

from __future__ import annotations

from app.energy_chat.evidence_hardening import (
    EvidenceBodyMetadata,
    check_evidence_freshness,
    compute_body_hash,
    validate_citations,
    verify_body_integrity,
)


def test_compute_body_hash_is_deterministic() -> None:
    body = "Deployment evidence: all CI checks passed."
    h1 = compute_body_hash(body)
    h2 = compute_body_hash(body)
    assert h1 == h2
    assert h1.startswith("sha256:")
    assert len(h1) == len("sha256:") + 64


def test_different_bodies_produce_different_hashes() -> None:
    h1 = compute_body_hash("evidence body one")
    h2 = compute_body_hash("evidence body two")
    assert h1 != h2


def test_verify_body_integrity_passes_on_match() -> None:
    body = "test evidence"
    expected = compute_body_hash(body)
    result = verify_body_integrity(body, expected)
    assert result.verified is True
    assert "matches" in result.reason


def test_verify_body_integrity_fails_on_mismatch() -> None:
    body = "real evidence"
    result = verify_body_integrity(body, "sha256:" + "a" * 64)
    assert result.verified is False
    assert "does not match" in result.reason


def test_validate_citations_detects_known_refs() -> None:
    answer = (
        "Based on [source:deployment_guide], the app requires Docker. "
        "See also [git:repo_config]."
    )
    known = ["source:deployment_guide", "git:repo_config", "test:ci_smoke"]
    result = validate_citations(answer, known)
    assert len(result.citations_found) == 2
    assert "source:deployment_guide" in result.valid_citations
    assert "git:repo_config" in result.valid_citations
    assert result.unknown_citations == []
    assert result.has_fabricated_citations is False


def test_validate_citations_detects_fabricated_refs() -> None:
    answer = "According to [source:made_up_evidence], the system is ready."
    known = ["source:deployment_guide"]
    result = validate_citations(answer, known)
    assert "source:made_up_evidence" in result.unknown_citations
    assert result.has_fabricated_citations is True


def test_validate_citations_handles_no_citations() -> None:
    answer = "The system is ready for deployment."
    result = validate_citations(answer, ["source:deployment_guide"])
    assert result.citations_found == []
    assert result.has_fabricated_citations is False


def test_freshness_project_sources_are_not_applicable() -> None:
    status = check_evidence_freshness(
        evidence_ref="source:project_docs", source_age_days=30
    )
    assert status == "not_applicable"


def test_freshness_stale_when_exceeds_max_age() -> None:
    status = check_evidence_freshness(
        evidence_ref="web:api_docs", source_age_days=120, max_age_days=90
    )
    assert status == "stale"


def test_freshness_current_within_max_age() -> None:
    status = check_evidence_freshness(
        evidence_ref="web:api_docs", source_age_days=30, max_age_days=90
    )
    assert status == "current"


def test_freshness_unknown_when_age_unavailable() -> None:
    status = check_evidence_freshness(
        evidence_ref="web:live_pricing", source_age_days=None
    )
    assert status == "unknown"


def test_evidence_body_metadata_defaults() -> None:
    meta = EvidenceBodyMetadata(evidence_ref="source:test")
    assert meta.body_hash is None
    assert meta.body_hash_status == "unavailable"
    assert meta.byte_count is None
