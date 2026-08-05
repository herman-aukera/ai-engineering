"""Evidence and citation hardening for Energy Aware Chat.

The contracts in this module contain hashes, verification states, freshness,
and citation references only. Evidence bodies are never stored in graph state,
ledger projections, or API responses.
"""

from __future__ import annotations

import hashlib
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.energy_chat.contracts import ProjectRagResult

EvidenceBodyHashStatus = Literal["hashed", "not_permitted", "unavailable"]
EvidenceVerificationStatus = Literal["verified", "failed", "not_checked"]
EvidenceFreshnessStatus = Literal["current", "stale", "not_applicable", "unknown"]


class EvidenceBodyMetadata(BaseModel):
    """Checkpoint-safe content integrity metadata for one evidence reference."""

    model_config = ConfigDict(extra="forbid")

    evidence_ref: str = Field(min_length=1)
    body_hash: str | None = Field(
        default=None,
        pattern=r"^(sha256:[0-9a-f]{64})?$",
    )
    body_hash_status: EvidenceBodyHashStatus = "unavailable"
    verification_status: EvidenceVerificationStatus = "not_checked"
    freshness_status: EvidenceFreshnessStatus = "unknown"
    byte_count: int | None = Field(default=None, ge=0)


class EvidenceVerificationResult(BaseModel):
    """Result of verifying one safe evidence body against its expected hash."""

    model_config = ConfigDict(extra="forbid")

    evidence_ref: str = Field(min_length=1)
    verified: bool
    reason: str = Field(min_length=1)
    expected_hash: str | None = None
    actual_hash: str | None = None


class CitationValidationResult(BaseModel):
    """Result of checking answer citations against exact known references."""

    model_config = ConfigDict(extra="forbid")

    citations_found: list[str] = Field(default_factory=list)
    valid_citations: list[str] = Field(default_factory=list)
    unknown_citations: list[str] = Field(default_factory=list)
    has_fabricated_citations: bool = False


class CandidateCitationValidation(BaseModel):
    """Immutable citation validation tied to one candidate version."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1)
    validation: CitationValidationResult


def compute_body_hash(body: str) -> str:
    """Compute SHA-256 over exact UTF-8 body bytes."""

    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def build_project_evidence_metadata(
    project_rag: ProjectRagResult | None,
) -> list[EvidenceBodyMetadata]:
    """Hash non-sensitive committed project chunks without retaining bodies."""

    if project_rag is None:
        return []
    return [
        EvidenceBodyMetadata(
            evidence_ref=chunk.evidence_ref,
            body_hash=compute_body_hash(chunk.content),
            body_hash_status="hashed",
            verification_status="verified",
            freshness_status="not_applicable",
            byte_count=len(chunk.content.encode("utf-8")),
        )
        for chunk in project_rag.results
    ]


def metadata_without_body(
    evidence_ref: str,
    *,
    permitted: bool,
    freshness_status: EvidenceFreshnessStatus | None = None,
) -> EvidenceBodyMetadata:
    """Record why an evidence reference has no content hash."""

    return EvidenceBodyMetadata(
        evidence_ref=evidence_ref,
        body_hash_status="unavailable" if permitted else "not_permitted",
        verification_status="not_checked",
        freshness_status=freshness_status
        or check_evidence_freshness(evidence_ref=evidence_ref),
    )


def verify_body_integrity(
    body: str,
    expected_hash: str,
    *,
    evidence_ref: str | None = None,
) -> EvidenceVerificationResult:
    """Verify a safe body without exposing its contents in the result."""

    actual = compute_body_hash(body)
    verified = actual == expected_hash
    return EvidenceVerificationResult(
        evidence_ref=evidence_ref or expected_hash[:18],
        verified=verified,
        reason=(
            "Evidence body matches expected hash"
            if verified
            else "Evidence body hash does not match expected hash"
        ),
        expected_hash=expected_hash if verified else None,
        actual_hash=actual if not verified else None,
    )


def validate_citations(
    answer_text: str,
    known_evidence_refs: list[str],
) -> CitationValidationResult:
    """Extract bracket citations and validate each exact reference."""

    pattern = re.compile(r"\[([a-zA-Z][a-zA-Z0-9_]*:[^\]]+)\]")
    unique_found = list(dict.fromkeys(pattern.findall(answer_text)))
    known_set = set(known_evidence_refs)
    valid = [citation for citation in unique_found if citation in known_set]
    unknown = [citation for citation in unique_found if citation not in known_set]
    return CitationValidationResult(
        citations_found=unique_found,
        valid_citations=valid,
        unknown_citations=unknown,
        has_fabricated_citations=bool(unknown),
    )


def validate_candidate_citations(
    *,
    candidate_id: str,
    answer_text: str,
    known_evidence_refs: list[str],
) -> CandidateCitationValidation:
    """Tie exact citation validation to one immutable candidate."""

    return CandidateCitationValidation(
        candidate_id=candidate_id,
        validation=validate_citations(answer_text, known_evidence_refs),
    )


def check_evidence_freshness(
    *,
    evidence_ref: str,
    source_age_days: int | None = None,
    max_age_days: int = 90,
) -> EvidenceFreshnessStatus:
    """Classify evidence freshness without guessing unavailable ages."""

    if evidence_ref.startswith(("file:", "source:", "git:", "test:", "ci:")):
        return "not_applicable"
    if source_age_days is None:
        return "unknown"
    return "stale" if source_age_days > max_age_days else "current"
