"""
LAYER: services semantic cache
RESPONSIBILITY: Provide deterministic semantic cache primitives for Session 04.
WHY IT EXISTS: Semantic cache starts in shadow mode so we can observe likely
               duplicate requests without serving approximate cached responses.
DEPENDS ON: hashlib, math, dataclasses

IMPORTANT:
This module deliberately does not call external embedding APIs. The deterministic
embedding is a local testable placeholder. Production embeddings can replace the
embedding function later without changing the shadow-mode control flow.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SemanticCacheCandidate:
    """A stored semantic cache candidate."""

    key: str
    bucket: str
    embedding: list[float]
    payload: dict[str, Any]


@dataclass(frozen=True)
class SemanticCacheMatch:
    """The best semantic candidate found for a query."""

    key: str
    bucket: str
    similarity: float
    payload: dict[str, Any]


def build_semantic_bucket(
    *,
    prompt_version: str,
    project_type: str,
    detail_level: str,
    output_format: str,
    model_identity: str,
) -> str:
    """
    Build the semantic cache namespace.

    The bucket includes every field that materially changes the estimate shape or
    expectation. Similarity should only be compared inside the same bucket.
    """

    return ":".join(
        [
            prompt_version,
            project_type,
            detail_level,
            output_format,
            model_identity,
        ]
    )


def deterministic_text_embedding(text: str, *, dimensions: int = 32) -> list[float]:
    """
    Return a deterministic local embedding for tests and shadow-mode plumbing.

    This is not a real semantic embedding. It is stable, cheap, and dependency
    free, which makes the cache contract testable before real embeddings are
    introduced.
    """

    normalized = " ".join(text.lower().split())
    vector: list[float] = []

    for index in range(dimensions):
        digest = hashlib.sha256(f"{index}:{normalized}".encode()).digest()
        integer = int.from_bytes(digest[:8], byteorder="big", signed=False)
        value = (integer / float(2**64 - 1)) * 2.0 - 1.0
        vector.append(value)

    norm = math.sqrt(sum(item * item for item in vector))
    if norm == 0:
        return [0.0 for _ in vector]

    return [item / norm for item in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Return cosine similarity for two vectors."""

    if len(left) != len(right) or not left:
        raise ValueError("vectors must have the same non-zero length")

    left_norm = math.sqrt(sum(item * item for item in left))
    right_norm = math.sqrt(sum(item * item for item in right))

    if left_norm == 0 or right_norm == 0:
        return 0.0

    score = sum(left_item * right_item for left_item, right_item in zip(left, right, strict=True))
    score = score / (left_norm * right_norm)

    return round(score, 6)


def find_best_semantic_candidate(
    *,
    query_embedding: list[float],
    candidates: list[SemanticCacheCandidate],
    threshold: float,
) -> SemanticCacheMatch | None:
    """
    Return the best candidate above threshold, or None.

    Shadow mode may record this match, but must not serve the candidate payload.
    """

    best: SemanticCacheMatch | None = None

    for candidate in candidates:
        similarity = cosine_similarity(query_embedding, candidate.embedding)

        if similarity < threshold:
            continue

        if best is None or similarity > best.similarity:
            best = SemanticCacheMatch(
                key=candidate.key,
                bucket=candidate.bucket,
                similarity=similarity,
                payload=candidate.payload,
            )

    return best
