"""Evidence and citation hardening for Energy Aware Chat.

Milestone 15: body hashing where permitted, verification, freshness checks,
and citation validation. Extends the existing EvidenceIntegrityMetadata
with content-level verification without exposing sensitive evidence bodies.
"""

from __future__ import annotations

import hashlib
import re
from typing import Literal

from pydantic import BaseModel, Field

EvidenceBodyHashStatus = Literal["hashed", "not_permitted", "unavailable"]


class EvidenceBodyMetadata(BaseModel):
    """Content-level integrity metadata for one evidence reference.

    The *body_hash* is only populated when the evidence body is safe to hash
    (non-sensitive, non-PII). When the body cannot be hashed, the status is
    ``"not_permitted"``. When a body was never provided, it is ``"unavailable"``.
    """

    evidence_ref: str = Field(min_length=1)
    body_hash: str | None = Field(
        default=None, pattern=r"^(sha256:[0-9a-f]{64})?$"
    )
    body_hash_status: EvidenceBodyHashStatus = "unavailable"
    byte_count: int | None = Field(default=None, ge=0)


class EvidenceVerificationResult(BaseModel):
    """Result of verifying that cited evidence matches its expected hash."""

    evidence_ref: str = Field(min_length=1)
    verified: bool
    reason: str = Field(min_length=1)
    expected_hash: str | None = None
    actual_hash: str | None = None


class CitationValidationResult(BaseModel):
    """Result of checking that answer citations reference known evidence."""

    citations_found: list[str] = Field(default_factory=list)
    valid_citations: list[str] = Field(default_factory=list)
    unknown_citations: list[str] = Field(default_factory=list)
    has_fabricated_citations: bool = False


def compute_body_hash(body: str) -> str:
    """Compute a SHA-256 content hash for an evidence body.

    Only call this when the body is confirmed non-sensitive. The hash
    covers the exact UTF-8 bytes of the body string.
    """
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def verify_body_integrity(
    body: str, expected_hash: str
) -> EvidenceVerificationResult:
    """Verify that an evidence body matches its expected hash.

    Returns a result with verification status and reason. Never exposes
    the body content in the reason string.
    """
    actual = compute_body_hash(body)
    verified = actual == expected_hash
    ref = expected_hash[:18] if expected_hash.startswith("sha256:") else expected_hash
    return EvidenceVerificationResult(
        evidence_ref=ref,
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
    answer_text: str, known_evidence_refs: list[str]
) -> CitationValidationResult:
    """Extract evidence-like citations from answer text and check them
    against a known set of evidence references.

    Citations are detected as patterns like ``[source:foo]``, ``[git:bar]``,
    ``[test:baz]``, or ``[ref:...]`` brackets in the answer.
    """
    pattern = re.compile(r"\[([a-zA-Z][a-zA-Z0-9_]*:[^\]]+)\]")
    found = pattern.findall(answer_text)
    unique_found = list(dict.fromkeys(found))
    known_set = set(known_evidence_refs)
    valid = [c for c in unique_found if c in known_set]
    unknown = [c for c in unique_found if c not in known_set]
    return CitationValidationResult(
        citations_found=unique_found,
        valid_citations=valid,
        unknown_citations=unknown,
        has_fabricated_citations=len(unknown) > 0,
    )


def check_evidence_freshness(
    *,
    evidence_ref: str,
    source_age_days: int | None = None,
    max_age_days: int = 90,
) -> Literal["current", "stale", "not_applicable", "unknown"]:
    """Determine freshness status for an evidence reference.

    When *source_age_days* is known, compares against *max_age_days*.
    When *source_age_days* is None, returns ``"unknown"`` rather than
    guessing.
    """
    if evidence_ref.startswith(("file:", "source:", "git:", "test:", "ci:")):
        return "not_applicable"
    if source_age_days is None:
        return "unknown"
    return "stale" if source_age_days > max_age_days else "current"
