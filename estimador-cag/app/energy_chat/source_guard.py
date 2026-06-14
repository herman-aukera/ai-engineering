"""Deterministic source requirement classifier for research and project modes."""

from __future__ import annotations

from app.energy_chat.contracts import (
    CriticFinding,
    EnergyChatRequest,
    EnergyPolicy,
    SourceNeedRequest,
    SourceNeedResult,
)

CURRENT_FACT_MARKERS = (
    "latest",
    "current",
    "currently",
    "today",
    "nowadays",
    "as of",
    "2026",
    "price",
    "pricing",
    "law",
    "legal",
    "regulation",
    "deadline",
    "model availability",
    "api documentation",
    "api docs",
    "version",
    "release notes",
)

PROJECT_SOURCE_MARKERS = (
    "branch",
    "repo",
    "repository",
    "codespaces",
    "validation gate",
    "tests",
    "pytest",
    "ruff",
    "ci",
    "readme",
    "task",
    "session",
    "lidr",
    "final project",
    "energy aware",
    "source pack",
)

TRUSTED_EVIDENCE_PREFIXES = (
    "retrieved:",
    "file:",
    "source:",
    "web:",
    "cmd:",
    "test:",
    "ci:",
    "git:",
    "manual:",
)


def classify_source_need(request: SourceNeedRequest) -> SourceNeedResult:
    """Classify whether a user/draft pair needs external or project evidence."""

    text = _combined_text(request.user_message, request.draft_answer)
    current_markers = _matched_markers(text, CURRENT_FACT_MARKERS)
    project_markers = _matched_markers(text, PROJECT_SOURCE_MARKERS)

    requires_current_sources = request.mode == "research" or bool(current_markers)
    requires_project_sources = request.mode == "project" or bool(project_markers)
    has_evidence = _has_trusted_evidence(request.evidence_refs)
    missing_evidence = (requires_current_sources or requires_project_sources) and not has_evidence

    if missing_evidence:
        decision = "sources_required"
        next_action = "Attach current or project evidence before accepting the answer."
    elif requires_current_sources or requires_project_sources:
        decision = "sources_recommended"
        next_action = "Keep the evidence references visible in the final answer."
    else:
        decision = "sources_not_required"
        next_action = "No source retrieval is required for this deterministic chat_lite check."

    reason_parts: list[str] = []
    if requires_current_sources:
        reason_parts.append("current or external facts are source-sensitive")
    if requires_project_sources:
        reason_parts.append("project-specific claims need repository or source-pack evidence")
    if not reason_parts:
        reason_parts.append("the request is local, stable, and not source-sensitive")

    return SourceNeedResult(
        decision=decision,
        requires_current_sources=requires_current_sources,
        requires_project_sources=requires_project_sources,
        missing_evidence=missing_evidence,
        detected_markers=[*current_markers, *project_markers],
        evidence_refs=request.evidence_refs,
        reasoning_summary="; ".join(reason_parts),
        next_action=next_action,
    )


def source_need_findings(
    request: EnergyChatRequest,
    policy: EnergyPolicy,
) -> list[CriticFinding]:
    """Convert source need classification into evaluator findings."""

    source_result = classify_source_need(
        SourceNeedRequest(
            user_message=request.user_message,
            draft_answer=request.draft_answer,
            mode=request.mode,
            evidence_refs=request.evidence_refs,
            metadata=request.metadata,
        )
    )
    if not source_result.missing_evidence:
        return []

    findings: list[CriticFinding] = []
    if source_result.requires_current_sources:
        findings.append(
            CriticFinding(
                critic="source_need_critic",
                violation_id="unsupported_current_claim",
                constraint_type="hard_repair",
                penalty=policy.penalties["unsupported_current_claim"],
                evidence="The answer contains current or external factual claims without trusted evidence references.",
                repair_hint="Retrieve or attach current evidence before accepting the answer.",
            )
        )
    if source_result.requires_project_sources:
        findings.append(
            CriticFinding(
                critic="source_need_critic",
                violation_id="missing_project_evidence",
                constraint_type="hard_repair",
                penalty=policy.penalties["missing_project_evidence"],
                evidence="The answer makes project-specific claims without repository or source-pack evidence references.",
                repair_hint="Attach project source, command, test, git, or CI evidence before accepting the answer.",
            )
        )
    return findings


def _combined_text(user_message: str, draft_answer: str | None) -> str:
    return f"{user_message}\n{draft_answer or ''}".casefold()


def _matched_markers(text: str, markers: tuple[str, ...]) -> list[str]:
    return [marker for marker in markers if marker in text]


def _has_trusted_evidence(evidence_refs: list[str]) -> bool:
    return any(ref.startswith(TRUSTED_EVIDENCE_PREFIXES) for ref in evidence_refs)
