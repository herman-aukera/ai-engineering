"""Evidence retrieval adapter for Energy Aware Chat.

The certified legacy lexical corpus remains available only when the final-project
support RAG is explicitly disabled. The final-project deployment enables the real
persisted embedding pipeline with ``EACHAT_SUPPORT_RAG_ENABLED=true``.
"""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from dataclasses import dataclass

from app.energy_chat.contracts import ProjectRagChunk, ProjectRagRequest, ProjectRagResult


@dataclass(frozen=True)
class ProjectSourceDocument:
    """One committed compatibility source available to the legacy retriever."""

    source_id: str
    title: str
    content: str

    @property
    def evidence_ref(self) -> str:
        return f"source:{self.source_id}"


PROJECT_SOURCE_CORPUS: tuple[ProjectSourceDocument, ...] = (
    ProjectSourceDocument(
        source_id="final_project_requirements",
        title="Final project mandatory requirements",
        content=(
            "The final project must demonstrate a complete AI system with a FastAPI AI "
            "service, RAG pipeline, agent layer, documented evals, a regression case, "
            "README, and deployment evidence through a public URL or demo video."
        ),
    ),
    ProjectSourceDocument(
        source_id="energy_chat_architecture",
        title="Energy Aware Chat staged architecture",
        content=(
            "Energy Aware Chat validates assistant answers with mode resolver, policy "
            "loader, critic pipeline, energy scorer, decider, repair path, and user-visible "
            "Energy Card. Modes include chat_lite, research, project, and tutor."
        ),
    ),
    ProjectSourceDocument(
        source_id="provider_fallback",
        title="DeepSeek primary with Kimi backup",
        content=(
            "Provider routing uses DeepSeek flash or pro as primary tiers and Kimi backup "
            "or backup_pro as fallback tiers. Live provider checks must be separated from "
            "normal deterministic CI and must never require committed secrets."
        ),
    ),
    ProjectSourceDocument(
        source_id="validation_ci",
        title="Validation and CI proof",
        content=(
            "A candidate is not accepted without ruff fix, ruff check, Python compile, "
            "focused tests, full pytest, diff checks, clean git status, and exact workflow "
            "proof for the target branch and commit."
        ),
    ),
    ProjectSourceDocument(
        source_id="benchmark_honesty",
        title="Benchmark honesty boundary",
        content=(
            "Benchmark output is measurement only until a fixed dataset and rubric prove an "
            "improvement. The allowed claim token is measurement_only_no_quality_claim. "
            "Do not claim frontier superiority or quality improvement without evidence."
        ),
    ),
    ProjectSourceDocument(
        source_id="deployment_safety",
        title="Safe deployment stance",
        content=(
            "Deployment should be manual, secret-safe, branch-bound, and health-checkable. "
            "A production-oriented MVP can provide Docker and GitHub workflow paths while "
            "still refusing to claim full production readiness without operational evidence."
        ),
    ),
)

TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")


def retrieve_project_context(request: ProjectRagRequest) -> ProjectRagResult:
    """Route to real final-project RAG or the explicit deterministic compatibility path."""

    if _truthy(os.getenv("EACHAT_SUPPORT_RAG_ENABLED")):
        from app.energy_chat.support_rag import get_support_rag_service

        return get_support_rag_service().retrieve(request)
    return _retrieve_legacy_project_context(request)


def _retrieve_legacy_project_context(request: ProjectRagRequest) -> ProjectRagResult:
    """Retain the pre-final-project lexical corpus for deterministic compatibility tests."""

    query_terms = _term_counts(request.query)
    ranked = sorted(
        (
            (
                _cosine_score(query_terms, _term_counts(f"{doc.title} {doc.content}")),
                doc,
            )
            for doc in PROJECT_SOURCE_CORPUS
        ),
        key=lambda item: (-item[0], item[1].source_id),
    )
    selected = ranked[: request.k]
    chunks = [
        ProjectRagChunk(
            source_id=doc.source_id,
            title=doc.title,
            content=doc.content,
            evidence_ref=doc.evidence_ref,
            score=round(score, 4),
        )
        for score, doc in selected
    ]
    evidence_refs = [chunk.evidence_ref for chunk in chunks]

    return ProjectRagResult(
        query=request.query,
        k=request.k,
        retrieval_strategy="deterministic_lexical_cosine_project_rag",
        results=chunks,
        evidence_refs=evidence_refs,
        grounding_summary=(
            "Retrieved committed Energy Aware project-source chunks using deterministic "
            "lexical cosine similarity. This is the CI-safe RAG baseline compatibility path "
            "and is not the final-project production RAG. Enable EACHAT_SUPPORT_RAG_ENABLED "
            "for the real persisted technical-support corpus."
        ),
    )


def _truthy(value: str | None) -> bool:
    return (value or "").strip().casefold() in {"1", "true", "yes", "on"}


def _term_counts(text: str) -> Counter[str]:
    return Counter(TOKEN_PATTERN.findall(text.casefold()))


def _cosine_score(query_terms: Counter[str], document_terms: Counter[str]) -> float:
    if not query_terms or not document_terms:
        return 0.0

    dot_product = sum(query_terms[token] * document_terms.get(token, 0) for token in query_terms)
    query_norm = math.sqrt(sum(value * value for value in query_terms.values()))
    document_norm = math.sqrt(sum(value * value for value in document_terms.values()))
    if query_norm == 0.0 or document_norm == 0.0:
        return 0.0

    return dot_product / (query_norm * document_norm)
